"""Thengin Thai: original score + foley + voice → out/mix.wav (mastered: −14 LUFS integrated, true peak ≤ −1.2 dBTP).
Score and foley are synthesised here (no samples). Levels as asked: dialogue voice 100 %, narrator (background voice) 75 %,
music and foley below both and ducked under every line.
Run: $LIB/.venv/bin/python mix.py   (needs events.json from `node core/render/events.mjs`)"""
import os, sys, json
import numpy as np, soundfile as sf, soxr
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB', '/root/lemo-opuscar')
sys.path.insert(0, os.path.join(LIB, 'core', 'audio'))
sys.path.append(os.path.join(HERE, '.pyenv'))
import sfx
from sfx import SR, t_, env_exp, bp, lp, hp, noise, norm, compress, add
import pyloudnorm

rng = np.random.default_rng(11)
EVJ = json.load(open(os.path.join(HERE, 'events.json')))
DUR, EV = EVJ['dur'], EVJ['ev']
N = int(DUR * SR) + SR
def buf(): return np.zeros((N, 2), np.float32)
music, foley, amb, voice = buf(), buf(), buf(), buf()
TL = {e['type']: e for e in EV}
def T(name): return {e['type'] for e in EV}
STOP = next(e['t'] for e in EV if e['type'] == 'stop')

# ———————————— instruments (synthesised) ————————————
def adsr(n, a=.01, r=.1):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e
def flute(f, d, v=1.0, vib=1):
    tt = t_(d); n = len(tt)
    vb = 1 + vib * .0045 * np.sin(2 * np.pi * 5.4 * tt) * np.clip((tt - .22) / .3, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vb) / SR
    tone = np.sin(ph) + .22 * np.sin(2 * ph) + .07 * np.sin(3 * ph)
    br = bp(noise(d), f * .9, min(f * 3.5, 20000)) * .05
    e = adsr(n, .07, min(.18, d * .4)) * (1 + .08 * np.sin(2 * np.pi * .9 * tt))
    return (tone * .8 + br) * e * v
def chenda(v=1.0, pitch=1.0):            # sharp stick on a tight cylindrical drum
    d = .35; tt = t_(d)
    f = 210 * pitch * (1 + .5 * np.exp(-tt / .012))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, .07)
    crack = bp(noise(d), 1200, 5000) * env_exp(d, .012) * .9
    return norm(body + crack) * v
def bass_drum(v=1.0):
    d = .9; tt = t_(d); f = 62 * (1 + .9 * np.exp(-tt / .03))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, .32) + .25 * np.sin(4 * np.pi * np.cumsum(f) / SR) * env_exp(d, .12)
    x += lp(noise(d), 400) * env_exp(d, .02) * .4
    return norm(x) * v
def cymbal(v=1.0):                       # small bell-metal hand cymbals
    d = 1.3; tt = t_(d)
    x = sum(a * np.sin(2 * np.pi * f * tt + rng.random() * 6) * env_exp(d, tau) for f, a, tau in [(2930, .5, .5), (4410, .4, .35), (5870, .35, .3), (7310, .25, .22), (3620, .3, .42)])
    x += hp(noise(d), 5000) * env_exp(d, .08) * .5
    return norm(x) * v
def gong(v=1.0, f0=118, fall=0, rise=0, d=4.0):
    tt = t_(d); bend = 1 - fall * .06 * (1 - np.exp(-tt / .6)) + rise * .08 * (1 - np.exp(-tt / .25))
    x = sum(a * np.sin(2 * np.pi * np.cumsum(f0 * m * bend) / SR) * env_exp(d, tau) for m, a, tau in [(1, 1, 1.6), (1.49, .6, 1.2), (2.03, .45, .9), (2.74, .3, .6), (3.4, .2, .4)])
    x *= np.clip(tt / .015, 0, 1); x += lp(noise(d), 900) * env_exp(d, .03) * .3
    return norm(x) * v
def woodblock(v=1.0):
    d = .12; tt = t_(d); x = np.sin(2 * np.pi * 880 * tt) * env_exp(d, .03) + .6 * np.sin(2 * np.pi * 1390 * tt) * env_exp(d, .018) + bp(noise(d), 2000, 6000) * env_exp(d, .004) * .4
    return norm(x) * v
def drone(d, freqs=(73.42, 110.0), v=1.0):
    tt = t_(d); x = 0
    for f in freqs:
        ph = 2 * np.pi * f * tt * (1 + .0008 * np.sin(2 * np.pi * .23 * tt))
        x = x + sum(np.sin(k * ph) / k ** 1.2 for k in range(1, 9))
    x = lp(x, 1400) * adsr(len(tt), 1.2, 1.5)
    return norm(x) * v
NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
D5, E5, Fs5, A5, B5, D6 = 74, 76, 78, 81, 83, 86
A4, B4, Gs4, C5, Fs4 = 69, 71, 68, 72, 66
def phrase(dst, t0, notes, beat=.625, v=1.0, pan=-.15):
    t = t0
    for m, b in notes:
        if m is not None: add(dst, flute(NOTE(m), b * beat * 1.02, v), t, 1, pan)
        t += b * beat
    return t

# ———————————— score from the timeline ————————————
TLD = {}
for e in EV: TLD.setdefault(e['type'], []).append(e)
press = TLD['drum'][0]['t']
add(music, bass_drum(1), press, .9, 0); add(music, cymbal(.6), press, .5, .25)
# opening motif under the first narration (huan-yin, D pentatonic)
MOTIF = [(D5, 1), (E5, .5), (Fs5, 1), (A5, 1.5), (Fs5, .5), (E5, 1), (D5, 2)]
phrase(music, 3.0, MOTIF, v=.5)
# conversation: low drone, pellet-drum and woodblock touches
add(music, drone(15.9 - 6.0, v=.22), 6.0, 1, 0)
for t in [6.3]: add(music, chenda(.7, 1.15), t, .6, -.2)
# near-silence: everything hard-cut at 15.9, one tap at 16.4 (in foley)
# the answer: flute alone, sorrowful colour (raised 4th, lowered 7th), then resolving home on "not only for us"
phrase(music, 17.0, [(A4, 2), (C5, 1), (B4, 1), (Gs4, 2), (A4, 2.5)], beat=.6, v=.42)
phrase(music, 22.4, [(Fs5, 1.2), (E5, 1), (D5, 1), (B4, 1), (D5, 2.6)], beat=.6, v=.42)
# the years: gong scrape in, accelerating chenda roll, a barrel drum + cymbal on each swap, big falling gong
sc = next(e['t'] for e in EV if e['type'] == 'scrape')
g = gong(.7, 96, d=2.5); g *= np.linspace(0, 1, len(g)) ** .5; add(music, bp(g, 200, 4000), sc, .5, 0)
swaps = [e['t'] for e in EV if e['type'] == 'swap'][:5] if False else [28.4, 30.0, 31.6, 33.2, 34.8]
prev = sc + .4
for i, s in enumerate(swaps):
    t = prev; gap = .32 - i * .045
    while t < s - .1: add(music, chenda(.35 + .5 * (t - prev) / (s - prev), 1 + .05 * (i % 2)), t, .55, rng.uniform(-.3, .3)); t += max(.07, gap * (1 - .6 * (t - prev) / (s - prev)))
    prev = s + .1
for e in TLD['drum'][1:]: add(music, bass_drum(e['v']), e['t'], .85, 0)
for e in TLD.get('cymbal', [])[1:]: add(music, cymbal(e['v']), e['t'], .5, .3)
for e in TLD['gong']:
    if e.get('fall'): add(music, gong(1, 98, fall=1, d=5), e['t'], .9, 0)
    if e.get('rise'): add(music, gong(.6, 330, rise=1, d=3), e['t'], .5, .1)
# the echo: the opening motif returns, slower
phrase(music, 36.0, MOTIF, beat=.72, v=.42)
# the ending: a low heartbeat drum under the last narration, the motif's head once more, a hard stop
for e in TLD.get('heartbeat', []):
    t = e['t']
    while t < e['t'] + e['d']: add(music, bass_drum(.45), t, .5, 0); add(music, bass_drum(.3), t + .28, .4, 0); t += 1.05
phrase(music, 46.2, [(D5, 1.5), (A4, 1), (D5, 4)], beat=.7, v=.4)
add(music, drone(STOP - 42.0, v=.16), 42.0, 1, 0)

# ———————————— foley ————————————
def flap(v=1.0):          # dry leather piece lifted off / swapped
    d = .32; tt = t_(d); x = bp(noise(d), 300, 2200) * env_exp(d, .07) * (1 + .6 * np.sin(2 * np.pi * 32 * tt)); return norm(x) * v
def pat(v=1.0):
    d = .12; x = lp(noise(d), 900) * env_exp(d, .02) + np.sin(2 * np.pi * 110 * t_(d)) * env_exp(d, .025) * .6; return norm(x) * v
def rustle(d, lo=1800, hi=7000, v=1.0):
    am = np.abs(lp(noise(d), 9)); am /= am.max() + 1e-9; x = bp(noise(d), lo, hi) * (.25 + am) * adsr(int(round(d * SR)), .3, .4); return norm(x) * v
def breeze(d, v=1.0):
    tt = t_(d); x = lp(noise(d), 500) * (.6 + .4 * np.sin(2 * np.pi * .17 * tt + 1)) * adsr(len(tt), 1.0, 1.0); return norm(x) * v
def chirp(v=1.0):
    d = .14; tt = t_(d); f = 3200 + 1800 * np.sin(np.pi * tt / d) + 400 * np.sin(2 * np.pi * 38 * tt); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / d) ** 2; return x * v
def trickle(d, v=1.0):
    n = int(round(d * SR)); x = np.zeros(n)
    for k in range(int(d * 40)):
        at = rng.integers(0, max(1, n - 2400)); f = rng.uniform(900, 2600); dd = .03; tt = t_(dd)
        x[at:at + len(tt)] += np.sin(2 * np.pi * f * (1 + 2 * tt) * tt) * env_exp(dd, .008) * rng.uniform(.3, 1)
    x += bp(noise(d), 1500, 6000) * .08; return norm(x * adsr(n, .1, .3)) * v
def slosh(v=1.0):
    d = .45; tt = t_(d); x = bp(noise(d), 300, 1500) * (.5 + .5 * np.sin(2 * np.pi * 11 * tt)) * np.sin(np.pi * tt / d); return norm(x) * v
def snuff(v=1.0):
    d = .5; x = hp(noise(d), 1200) * env_exp(d, .05) + bp(noise(d), 4000, 9000) * env_exp(d, .25) * .25; return norm(x) * v
def creak(d, v=1.0):
    tt = t_(d); f = 140 + 30 * np.sin(2 * np.pi * .7 * tt); pulses = (np.sin(2 * np.pi * np.cumsum(f) / SR) > .97).astype(float)
    x = bp(pulses + noise(d) * .02, 400, 2500) * adsr(len(tt), .2, .4); return norm(x) * v
for e in EV:
    ty, t, v = e['type'], e['t'], e.get('v', 1.0)
    if ty == 'room': add(amb, sfx.brown(e['d'] if e['d'] < DUR else DUR) * .06, t, 1, 0)
    elif ty == 'ignite': add(foley, sfx.ignite(v), t, .55, 0)
    elif ty in ('liftoff', 'swap'): add(foley, flap(v), t, .5, rng.uniform(-.2, .2))
    elif ty == 'rodtap': add(foley, sfx.clack(.55, v), t, .35, 0)
    elif ty == 'step': add(foley, sfx.step(v), t, .4, -.2)
    elif ty == 'hop': add(foley, flap(.4), t, .3, -.2)
    elif ty == 'land': add(foley, sfx.thump(v, 90), t, .5, -.2)
    elif ty == 'woodblock': add(foley, woodblock(v), t, .55, .15)
    elif ty == 'pat': add(foley, pat(v), t, .4, .2)
    elif ty == 'slosh': add(foley, slosh(v), t, .35, -.15)
    elif ty == 'cut': add(foley, sfx.whoosh(.3, .4), t, .3, 0)
    elif ty == 'fronds': add(amb, rustle(e['d'], v=.5), t, 1, -.3)
    elif ty == 'breeze': add(amb, breeze(e['d'], v * .35), t, 1, 0)
    elif ty == 'birds':
        for k in range(int(e['d'] * 1.6)): add(amb, chirp(rng.uniform(.08, .16)), t + rng.uniform(0, e['d']), 1, rng.uniform(-.6, .6))
    elif ty == 'pour': add(foley, trickle(e['d'], .45), t, 1, 0)
    elif ty == 'snuff': add(foley, snuff(v), t, .3, 0)
    elif ty == 'cloth': add(foley, rustle(e['d'], 600, 4000, .35), t, 1, 0)
    elif ty == 'carry': add(foley, creak(e['d'], .3), t, 1, -.3)
    elif ty == 'scrape': pass

# ———————————— voice ————————————
CUTS = {'g2': [(2.45, 3.1)]}
LEVEL = {'narrator': .75}            # "background voice 75": the narrator at 75 % of the dialogue level (−2.5 dB)
def reverb(x, wet=.1):
    d = .7; ir = noise(d) * env_exp(d, .16); ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
    return x + fftconvolve(x, ir)[:len(x)] * wet
vmask = np.zeros(N)
for e in [e for e in EV if e['type'] == 'vo']:
    x, sr = sf.read(os.path.join(HERE, 'voice', 'out', e['id'] + '.wav'), dtype='float32')
    if x.ndim > 1: x = x.mean(1)
    for a, b in reversed(CUTS.get(e['id'], [])):        # fluency: trim the long pause, with a short crossfade
        ia, ib, f = int(a * sr), int(b * sr), int(.03 * sr); seg = x[ib:ib + f] * np.linspace(0, 1, f) + x[ia - f:ia] * np.linspace(1, 0, f)
        x = np.concatenate([x[:ia - f], seg, x[ib + f:]])
    x = soxr.resample(x, sr, SR)
    x = hp(x, 80)
    x = compress(x / (np.abs(x).max() + 1e-9) * .9, thr=.3, ratio=3.0)
    x = x / (np.sqrt(np.mean(x[np.abs(x) > .02] ** 2)) + 1e-9) * .16          # every line to the same speech RMS
    x = reverb(x, .09) * LEVEL.get(e['who'], 1.0)
    pan = {'ammumma': .12, 'oldappu': .12, 'appu': -.12, 'minnu': -.12}.get(e['who'], 0)
    add(voice, x, e['t'], 1, pan)
    i0 = int(e['t'] * SR); vmask[i0:i0 + len(x)] = 1

# ducking envelope: 60 ms attack, 350 ms release
def smooth_env(m, att=.06, rel=.35):
    out = np.zeros_like(m); a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR)); y = 0.0
    # run on a decimated signal for speed
    k = 48; md = m[::k]; od = np.zeros_like(md); y = 0.0; a, r = np.exp(-k / (att * SR)), np.exp(-k / (rel * SR))
    for i, v in enumerate(md): y = a * y + (1 - a) * v if v > y else r * y + (1 - r) * v; od[i] = y
    return np.repeat(od, k)[:len(m)]
env = smooth_env(vmask)[:, None]
mus_g = 1 - env * (1 - 10 ** (-12 / 20))       # music −12 dB under any voice
fol_g = 1 - env * (1 - 10 ** (-4 / 20))        # foley −4 dB
amb_g = 1 - env * (1 - 10 ** (-6 / 20))
# hard cuts: the near-silence before the answer, and the final stop (only the lamp's last sizzle may ring on)
def gate(x, t0, t1, fade=.025):
    i0, i1, f = int(t0 * SR), int(t1 * SR), int(fade * SR); x[i0:i0 + f] *= np.linspace(1, 0, f)[:, None]; x[i0 + f:i1] = 0
    if i1 < len(x): x[i1:i1 + f] *= np.linspace(0, 1, min(f, len(x) - i1))[:, None]
for b in (music, amb): gate(b, 15.9, 16.9)
gate(music, STOP, DUR + 1, .02); gate(amb, STOP, DUR + 1, .02)
# balance: music bed sits ~8 dB under the dialogue before ducking
def rms(x): return np.sqrt(np.mean(x[np.abs(x).max(1) > 1e-4] ** 2)) if np.any(np.abs(x) > 1e-4) else 1
music *= .16 * 10 ** (-8 / 20) / rms(music)
mix = voice + music * mus_g + foley * .55 * fol_g + amb * .5 * amb_g
mix = mix[:int(DUR * SR)]
# measure per-band low end (keep 20–120 Hz modest)
lo = sosfilt(butter(4, 120, 'low', fs=SR, output='sos'), mix[:, 0]); print(f'low band vs full: {20*np.log10(rms(lo[:,None])/rms(mix[:, :1])):.1f} dB')
# ———————————— master: −14 LUFS, true peak ≤ −1.2 dBTP (4× oversampled limiter) ————————————
meter = pyloudnorm.Meter(SR)
L = meter.integrated_loudness(mix); mix *= 10 ** ((-14 - L) / 20)
def true_peak(x): return np.abs(resample_poly(x, 4, 1, axis=0)).max()
ceil = 10 ** (-1.2 / 20)
for it in range(6):
    up = resample_poly(mix, 4, 1, axis=0); pk = np.abs(up).max(1)
    g = np.minimum(1, ceil / np.maximum(pk, 1e-9))
    # smooth gain (5 ms look-ahead/attack, 80 ms release) on the oversampled envelope
    k = 4 * 48; gd = np.minimum.reduceat(g, np.arange(0, len(g), k)); y = 1.0; out = np.empty_like(gd); rr = np.exp(-1 / (80 / 1))
    for i in range(len(gd) - 1, -1, -1): pass
    gs = np.empty_like(gd); y = 1.0
    for i in range(len(gd)): y = min(gd[i], y + (1 - y) * .02); gs[i] = y
    gs = np.minimum(gs, np.concatenate([gs[1:], gs[-1:]]))          # look-ahead one block
    gain = np.repeat(gs, k)[:len(g)][::4][:len(mix)]
    mix *= gain[:, None]
    L = meter.integrated_loudness(mix); mix *= 10 ** ((-14 - L) / 20)
    if true_peak(mix) <= ceil: break
print(f'integrated {meter.integrated_loudness(mix):.2f} LUFS, true peak {20*np.log10(true_peak(mix)):.2f} dBTP')
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
sf.write(os.path.join(HERE, 'out', 'mix.wav'), mix.astype(np.float32), SR, subtype='PCM_24')
print('wrote out/mix.wav', mix.shape[0] / SR, 's')
