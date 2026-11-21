"""Synthesised score: soft nostalgic piano + gentle string pad, following the
film's emotional arc (playful -> lullaby -> time passing -> quiet ending).
writes build/music.wav (48 kHz stereo)"""
import json, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
rng = np.random.default_rng(7)

NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)

def piano(f, dur, vel=0.5):
    n = int(SR * (dur + 1.8)); t = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * (1 + 0.0004 * k * k)
        if fk > 15000: break
        amp = (1 / k ** 1.25) * (1.0 if k == 1 else 0.6)
        dec = 0.55 + 0.45 * k + f / 900
        y += amp * np.exp(-t * dec) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28))
    att = np.minimum(1, t / 0.004)
    rel = np.where(t > dur, np.exp(-(t - dur) * 5.0), 1.0)
    ham = rng.normal(0, 1, n) * np.exp(-t * 300) * 0.05
    y = (y * att * rel + ham) * vel * (0.7 + 0.3 * (220 / max(f, 110)) ** 0.3)
    return y

def pad(freqs, dur, vel=0.12, att=1.6, relt=1.8, bright=1400):
    n = int(SR * (dur + relt)); t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for det in (-0.004, 0.0, 0.0045):
            ph = 2 * np.pi * f * (1 + det) * t + rng.uniform(0, 6.28)
            y += sum(np.sin(ph * k) / k for k in range(1, 7))
    env = np.minimum(1, t / att) * np.where(t > dur, np.exp(-(t - dur) * 2.2), 1.0)
    y = sosfilt(butter(2, bright, "lp", fs=SR, output="sos"), y) * env
    y *= 1 + 0.05 * np.sin(2 * np.pi * 0.25 * t)
    return y * vel / max(1, len(freqs))

def add(buf, x, at):
    i = int(at * SR)
    if i >= len(buf): return
    x = x[:len(buf) - i]
    buf[i:i + len(x)] += x

CH = {  # chord tones (bass, voicing)
    "C": ("C3", ["C4", "E4", "G4"]), "G": ("G2", ["B3", "D4", "G4"]), "Am": ("A2", ["C4", "E4", "A4"]),
    "F": ("F2", ["A3", "C4", "F4"]), "Em": ("E2", ["B3", "E4", "G4"]), "Dm": ("D3", ["D4", "F4", "A4"]),
    "Bb": ("A#2", ["A#3", "D4", "F4"]), "Gsus": ("G2", ["C4", "D4", "G4"]),
}

def section(L, R_, start, end, chords, bpm, pattern, vel, padvel, melody=None, mel_vel=0.32, pan=0.15, bright=1400, octave_up=False):
    beat = 60 / bpm; bar = beat * 4
    t = start; i = 0
    while t < end - 0.05:
        name = chords[i % len(chords)]
        bass, voic = CH[name]
        bl = min(bar, end - t)
        p = pad([hz(n) for n in voic] + [hz(bass)], bl, vel=padvel, bright=bright)
        add(L, p, t); add(R_, p, t)
        add(L, piano(hz(bass), bar * 0.9, vel * 0.8), t); add(R_, piano(hz(bass), bar * 0.9, vel * 0.8), t)
        notes = [hz(n) for n in voic]
        if octave_up:
            notes = notes + [notes[0] * 2]
        for j, (b, idx) in enumerate(pattern):
            tt = t + b * beat
            if tt >= end: break
            f = notes[idx % len(notes)] * (2 if idx >= len(notes) else 1)
            x = piano(f, beat * 1.5, vel * (0.85 if j % 2 else 1.0))
            pn = pan * (1 if idx % 2 else -1)
            add(L, x * (1 - pn), tt); add(R_, x * (1 + pn), tt)
        if melody:
            for (b, nm, ln) in melody[i % len(melody)]:
                tt = t + b * beat
                if tt >= end or nm is None: continue
                x = piano(hz(nm), ln * beat, mel_vel)
                add(L, x * 1.05, tt); add(R_, x * 0.95, tt)
        t += bar; i += 1

def reverb(x, secs=2.6, wet=0.32):
    n = int(SR * secs); t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t * 6.5 / secs)
    ir = sosfilt(butter(1, 5000, "lp", fs=SR, output="sos"), ir)
    ir[:int(0.012 * SR)] = 0; ir /= np.sqrt(np.sum(ir ** 2))
    w = fftconvolve(x, ir)[:len(x)]
    return (1 - wet) * x + wet * w * 0.6

def main():
    tl = json.load(open(os.path.join(ROOT, "build", "timeline.json")))
    total = sum(s["frames"] for s in tl) / 30
    st = {s["name"]: s["start"] / 30 for s in tl}
    N = int(SR * (total + 1)); L = np.zeros(N); R_ = np.zeros(N)
    arp = [(0, 0), (0.5, 1), (1, 2), (1.5, 1), (2, 3), (2.5, 1), (3, 2), (3.5, 1)]
    soft = [(0, 0), (1, 1), (2, 2), (3, 1)]
    lull = [(0, 0), (1, 2), (2, 3), (3, 2)]
    # A: warm, playful memories (title -> lane)
    melA = [[(0, "E5", 1.5), (1.5, "G5", 0.5), (2, "E5", 1), (3, "D5", 1)],
            [(0, "D5", 2), (2, "B4", 1), (3, "D5", 1)],
            [(0, "C5", 1.5), (1.5, "E5", 0.5), (2, "A4", 2)],
            [(0, "A4", 1), (1, "C5", 1), (2, "F5", 1.5), (3.5, "E5", 0.5)]]
    section(L, R_, 0.0, st["s4_wide"] - 0.3, ["C", "G", "Am", "F"], 78, arp, 0.20, 0.10, melody=melA, mel_vel=0.22)
    # B: night lullaby (bedtime story)
    melB = [[(0, "C6", 1), (1, "A5", 1), (2, "G5", 2)], [(0, "F5", 1), (1, "A5", 1), (2, "C6", 2)],
            [(0, "D6", 1), (1, "C6", 1), (2, "A5", 2)], [(0, "G5", 2), (2, "E5", 2)]]
    section(L, R_, st["s4_wide"] - 0.3, st["s5_timelapse"], ["F", "C", "Dm", "Bb"], 64, lull, 0.13, 0.08, melody=melB,
            mel_vel=0.12, bright=1100)
    # C: time passing - strings swell
    section(L, R_, st["s5_timelapse"], st["s5_return"], ["Am", "F", "C", "G"], 66, soft, 0.16, 0.22, bright=2200)
    # D: years later -> ending (slow, tender, emotional)
    melD = [[(0, "E5", 2), (2, "D5", 1), (3, "C5", 1)], [(0, "C5", 3), (3, "A4", 1)],
            [(0, "G4", 1.5), (1.5, "C5", 0.5), (2, "E5", 2)], [(0, "D5", 3), (3, None, 1)]]
    section(L, R_, st["s5_return"], st["s6_final"], ["Am", "F", "C", "G"], 60, soft, 0.15, 0.13, melody=melD, mel_vel=0.2)
    # final: swell under the last line, resolve on C, then a lone high note
    melE = [[(0, "E5", 2), (2, "G5", 2)], [(0, "A5", 3), (3, "G5", 1)], [(0, "E5", 2), (2, "D5", 2)], [(0, "C5", 4)]]
    section(L, R_, st["s6_final"], total - 2.6, ["F", "G", "Am", "C"], 60, soft, 0.15, 0.2, melody=melE, mel_vel=0.2, bright=2000)
    tail = st["s6_final"] + 13.0 - 2.6
    add(L, pad([hz("C3"), hz("G3"), hz("E4"), hz("C5")], 1.5, vel=0.25, relt=2.5), tail); add(R_, pad([hz("C3"), hz("G3"), hz("E4"), hz("C5")], 1.5, vel=0.25, relt=2.5), tail)
    add(L, piano(hz("C6"), 2.0, 0.18), tail + 0.4); add(R_, piano(hz("C6"), 2.0, 0.18), tail + 0.4)
    L, R_ = reverb(L), reverb(R_)
    y = np.stack([L, R_], 1)[:int(SR * total)]
    # gentle fades
    fi = int(SR * 1.2); y[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = int(SR * 2.5); y[-fo:] *= np.linspace(1, 0, fo)[:, None]
    y /= np.max(np.abs(y)) + 1e-9
    sf.write(os.path.join(ROOT, "build", "music.wav"), (y * 0.9).astype(np.float32), SR)
    print("music", total)

if __name__ == "__main__":
    main()
