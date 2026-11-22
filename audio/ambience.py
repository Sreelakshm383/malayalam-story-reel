"""Ambience + foley bed (birds, wind, footsteps, kitchen fire, crickets, rain,
clock) laid out from build/timeline.json. writes build/ambience.wav"""
import json, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
rng = np.random.default_rng(11)

def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "bp", fs=SR, output="sos"), x)
def lp(x, f): return sosfilt(butter(2, f, "lp", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "hp", fs=SR, output="sos"), x)

def pink(n):
    w = rng.normal(0, 1, n)
    return lp(w, 900) + 0.3 * lp(w, 3000)

def env(n, fade=0.8):
    e = np.ones(n); k = min(int(fade * SR), n // 2)
    if k > 0:
        e[:k] = np.linspace(0, 1, k); e[-k:] = np.linspace(1, 0, k)
    return e

def chirp(kind):
    if kind == 0:   # short sweeping tweet
        d = rng.uniform(0.05, 0.12); t = np.arange(int(d * SR)) / SR
        f0, f1 = rng.uniform(2800, 4200), rng.uniform(3500, 6000)
        ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * (t / d) ** 0.5) / SR
        return np.sin(ph) * np.sin(np.pi * t / d) ** 2
    d = rng.uniform(0.25, 0.4); t = np.arange(int(d * SR)) / SR   # koel-like two-tone whistle
    f = 1300 + 500 * (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 1.5 * 0.6

def birds(n, density=1.0, far=False):
    L = np.zeros(n); R = np.zeros(n)
    t = rng.uniform(0, 0.8)
    while t < n / SR - 0.5:
        kind = 1 if rng.random() < 0.12 else 0
        reps = rng.integers(1, 5) if kind == 0 else 2
        pan = rng.uniform(-0.8, 0.8); g = rng.uniform(0.15, 0.45) * (0.4 if far else 1)
        for r in range(reps):
            c = chirp(kind) * g
            i = int((t + r * rng.uniform(0.09, 0.16)) * SR)
            if i + len(c) < n:
                L[i:i + len(c)] += c * (1 - pan) / 2; R[i:i + len(c)] += c * (1 + pan) / 2
        t += rng.exponential(1.6 / density)
    return L, R

def wind(n, amt=1.0):
    t = np.arange(n) / SR
    w = lp(rng.normal(0, 1, n), 380) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * t + 1) * np.sin(2 * np.pi * 0.21 * t))
    leaves = bp(rng.normal(0, 1, n), 2500, 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t)) ** 2 * 0.25
    return (w * 0.5 + leaves) * amt

def steps(n, rate, gain, dur_s=None, start=0.0, soft=True):
    y = np.zeros(n); t = start
    end = n / SR if dur_s is None else start + dur_s
    while t < end:
        k = int(0.05 * SR); i = int(t * SR)
        s = lp(rng.normal(0, 1, k), 260 if soft else 900) * np.exp(-np.arange(k) / SR * 70)
        s += 0.3 * bp(rng.normal(0, 1, k), 1500, 4000) * np.exp(-np.arange(k) / SR * 160)   # gravel grit
        if i + k < n: y[i:i + k] += s * gain * rng.uniform(0.8, 1.1)
        t += 1 / rate * rng.uniform(0.95, 1.05)
    return y

def crickets(n):
    t = np.arange(n) / SR; y = np.zeros(n)
    for f, rate, ph, g in ((4400, 2.3, 0, 0.12), (5200, 1.7, 1.3, 0.08), (3900, 2.9, 2.0, 0.06)):
        carrier = np.sin(2 * np.pi * f * t)
        pulse = (np.sin(2 * np.pi * 32 * t) > 0.2).astype(float)
        burst = (np.sin(2 * np.pi * rate * t + ph) > 0.55).astype(float)
        y += carrier * lp(pulse * burst, 400) * g
    return y

def fire(n):
    y = lp(rng.normal(0, 1, n), 500) * 0.08
    for _ in range(int(n / SR * 9)):
        i = rng.integers(0, n - 2000); k = rng.integers(200, 1500)
        y[i:i + k] += hp(rng.normal(0, 1, k), 1500) * np.exp(-np.arange(k) / k * 5) * rng.uniform(0.05, 0.3)
    return y

def rain(n):
    t = np.arange(n) / SR
    y = bp(rng.normal(0, 1, n), 1200, 9000) * 0.35 + lp(rng.normal(0, 1, n), 300) * 0.25
    for _ in range(int(n / SR * 60)):
        i = rng.integers(0, n - 400)
        y[i:i + 300] += hp(rng.normal(0, 1, 300), 3000) * np.exp(-np.arange(300) / 40) * rng.uniform(0.1, 0.4)
    return y

def clock(n):
    y = np.zeros(n); t = 0.3
    while t < n / SR:
        k = 600; i = int(t * SR)
        if i + k < n:
            y[i:i + k] += bp(rng.normal(0, 1, k), 2000, 6000) * np.exp(-np.arange(k) / 60) * 0.35
        t += 1.0
    return y

def main():
    tl = json.load(open(os.path.join(ROOT, "build", "timeline.json")))
    total = sum(s["frames"] for s in tl) / 30
    N = int(SR * total); L = np.zeros(N); R = np.zeros(N)
    def put(name, yl, yr=None, fade=0.6, pre=0.3, post=0.3):
        s = next(x for x in tl if x["name"] == name)
        a = max(0, int((s["start"] / 30 - pre) * SR))
        b = min(N, int(((s["start"] + s["frames"]) / 30 + post) * SR))
        n = b - a
        yl = yl(n) if callable(yl) else yl
        yr = yl if yr is None else (yr(n) if callable(yr) else yr)
        e = env(n, fade)
        L[a:b] += yl[:n] * e; R[a:b] += yr[:n] * e
    day = ["title", "s1_run", "s1_gma", "s1_gpa", "s1_hug", "s3_walk", "s3_two", "s3_shop"]
    for nm in day:
        put(nm, lambda n: wind(n, 0.5), lambda n: wind(n, 0.5))
        bl = {}
        def bL(n, nm=nm):
            bl[nm] = birds(n, 1.2 if nm != "s1_gma" else 0.8); return bl[nm][0]
        put(nm, bL, lambda n, nm=nm: bl[nm][1])
    put("s1_run", lambda n: steps(n, 4.8, 0.7, start=0.0))
    put("s1_hug", lambda n: steps(n, 4.8, 0.6, dur_s=1.7, start=0.3))
    put("s3_walk", lambda n: steps(n, 1.7, 0.45) + steps(n, 2.5, 0.3, start=0.2))
    put("s3_two", lambda n: steps(n, 1.7, 0.45) + steps(n, 2.5, 0.3, start=0.2))
    put("s3_shop", lambda n: steps(n, 1.7, 0.4, dur_s=2.0) + steps(n, 2.5, 0.25, dur_s=2.0, start=0.2))
    for nm in ("s2_wide", "s2_child", "s2_gma"):
        put(nm, lambda n: fire(n) + lp(rng.normal(0, 1, n), 200) * 0.03)
        put(nm, lambda n: birds(n, 0.4, far=True)[0], lambda n: birds(n, 0.4, far=True)[1])
    for nm in ("s4_wide", "s4_story", "s4_eager", "s4_sleep"):
        put(nm, lambda n: crickets(n) * 0.9, lambda n: np.roll(crickets(n), 2400) * 0.9)
    # time-lapse: wind rises, rain sweeps through
    s = next(x for x in tl if x["name"] == "s5_timelapse")
    n = int(s["frames"] / 30 * SR)
    tt = np.arange(n) / n
    storm = np.sin(np.pi * np.clip((tt - 0.2) / 0.6, 0, 1))
    put("s5_timelapse", lambda n: wind(n, 1.6) + rain(n) * np.interp(np.arange(n) / n, tt, storm),
        lambda n: wind(n, 1.6) + rain(n) * np.interp(np.arange(n) / n, tt, storm))
    for nm in ("s5_return", "s6_veranda", "s6_final"):
        put(nm, lambda n: wind(n, 0.7), lambda n: wind(n, 0.7))
        put(nm, lambda n: birds(n, 0.35, far=True)[0], lambda n: birds(n, 0.35, far=True)[1])
    put("s5_return", lambda n: steps(n, 1.8, 0.55, dur_s=3.3, start=0.0, soft=False))
    for nm in ("s5_face", "s5_photo", "s6_toys", "s6_photo"):
        put(nm, lambda n: clock(n) * 0.5 + lp(rng.normal(0, 1, n), 250) * 0.02)
    y = np.stack([L, R], 1)
    y /= np.max(np.abs(y)) + 1e-9
    sf.write(os.path.join(ROOT, "build", "ambience.wav"), (y * 0.8).astype(np.float32), SR)
    print("ambience", total)

if __name__ == "__main__":
    main()
