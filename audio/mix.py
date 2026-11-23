"""Final mix: dialogue on top, music + ambience well below and side-chain ducked
under every line. writes build/mix.wav (48 kHz stereo, normalised later to -14 LUFS)"""
import json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import fftconvolve, butter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from reel import B, CFG, STORY
SR = 48000

def db(x): return 10 ** (x / 20)

def loud(x):
    """rough loudness (RMS of active parts, dBFS)"""
    m = x if x.ndim == 1 else x.mean(1)
    a = np.abs(m) > 1e-3
    return 20 * np.log10(np.sqrt(np.mean(m[a] ** 2)) + 1e-9) if a.any() else -99

def room(x, secs, wet, seed=3):
    rng = np.random.default_rng(seed)
    n = int(SR * secs); t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t * 7 / secs)
    ir = sosfilt(butter(1, 4000, "lp", fs=SR, output="sos"), ir); ir[:int(0.008 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    return (1 - wet) * x + wet * fftconvolve(x, ir)[:len(x)] * 0.7

def main():
    tl = json.load(open(os.path.join(B, "timeline.json")))
    total = sum(s["frames"] for s in tl) / 30
    N = int(SR * total)
    V = np.zeros((N, 2))
    for s in tl:
        for c in s["cues"]:
            y, _ = sf.read(os.path.join(B, "voice", c["id"] + ".wav"))
            if c["speaker"] == "narrator":
                y = room(y, 1.6, 0.18)
            elif c["speaker"] == "adult":           # inner voice: softer, more space
                y = room(y, 2.2, 0.32) * 0.92
            else:
                y = room(y, 0.6, 0.08)
            i = int((s["start"] / 30 + c["start"]) * SR)
            pan = {"child": 0.06, "grandma": -0.05, "grandpa": -0.08}.get(c["speaker"], 0.0)
            seg = y[:max(0, N - i)]
            V[i:i + len(seg), 0] += seg * (1 - pan); V[i:i + len(seg), 1] += seg * (1 + pan)
    M, _ = sf.read(os.path.join(B, "music.wav")); M = M[:N]
    A, _ = sf.read(os.path.join(B, "ambience.wav")); A = A[:N]
    if len(M) < N: M = np.pad(M, ((0, N - len(M)), (0, 0)))
    if len(A) < N: A = np.pad(A, ((0, N - len(A)), (0, 0)))
    # side-chain envelope from dialogue (fast attack, slow release, with look-ahead)
    hop = 480
    e = np.sqrt(np.convolve(V.mean(1) ** 2, np.ones(hop) / hop, "same"))[::hop]
    act = (e > 0.012).astype(float)
    sm = np.zeros_like(act); g = 0
    for k in range(len(act) - 1, -1, -1):     # look-ahead: start ducking 0.25 s before speech
        g = max(act[k], g * 0.96); sm[k] = g
    out = np.zeros_like(sm); g = 0
    for k in range(len(sm)):
        g = sm[k] if sm[k] > g else g * 0.985
        out[k] = g
    duck = np.interp(np.arange(N), np.arange(len(out)) * hop, out)
    vl = loud(V)
    music_gain = db(vl - loud(M) - 9) * (1 - duck * (1 - db(-8)))     # ~9 dB under voice, 17 dB under while talking
    amb_gain = db(vl - loud(A) - 17) * (1 - duck * (1 - db(-4)))
    mix = V + M * music_gain[:, None] + A * amb_gain[:, None]
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    sf.write(os.path.join(B, "mix.wav"), mix.astype(np.float32), SR)
    print("voice", round(vl, 1), "music", round(loud(M * music_gain[:, None]), 1), "amb", round(loud(A * amb_gain[:, None]), 1))

if __name__ == "__main__":
    main()
