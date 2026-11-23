"""Episode 1 of "ആ പഴയ വീട്": lay the dialogue out on a shot list, add a night ambience
bed (crickets, wall clock, steel plates) and a low tension score, and write:
  build/pazhaya_veedu/episode_audio.wav   the finished soundtrack
  production/pazhaya_veedu/spec.json      shot cut points + subtitles for assemble_episode.py

usage: python3 production/pazhaya_veedu/build_audio.py
(run audio/voices.py or audio/voices_eleven.py with REEL_STORY=pazhaya_veedu first)
"""
import json, os, sys
os.environ["REEL_STORY"] = "pazhaya_veedu"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [ROOT, os.path.join(ROOT, "audio")]
import numpy as np, soundfile as sf
from reel import B, CFG
import ambience as A, music as M
from mix import room

SR = 48000
# (shot, line ids, lead-in before first line, gap between lines, tail after last line, minimum length)
SHOTS = [
    ("s01_house",   [],             0.0, 0.0, 0.0, 4.5),
    ("s02_table",   ["l01"],        2.2, 0.0, 0.5, 0.0),
    ("s03_meera",   ["l02"],        0.4, 0.0, 0.5, 0.0),
    ("s04_amma",    ["l03"],        0.3, 0.0, 0.5, 0.0),
    ("s05_meera",   ["l04"],        0.4, 0.0, 0.6, 0.0),
    ("s06_achan",   ["l05"],        0.8, 0.0, 0.5, 0.0),
    ("s07_meera",   ["l06"],        0.5, 0.0, 0.6, 0.0),
    ("s08_silence", [],             0.0, 0.0, 0.0, 2.8),
    ("s09_appu",    ["l07"],        0.3, 0.0, 0.5, 0.0),
    ("s10_meera",   ["l08"],        0.3, 0.0, 0.4, 0.0),
    ("s11_appu",    ["l09"],        0.3, 0.0, 0.6, 0.0),
    ("s12_meera",   [],             0.0, 0.0, 0.0, 2.6),
    ("s13_achan",   ["l10"],        0.5, 0.0, 0.5, 0.0),
    ("s14_meera",   ["l11"],        0.3, 0.0, 0.5, 0.0),
    ("s15_achan",   ["l12"],        0.6, 0.0, 3.4, 0.0),
    ("s16_end",     [],             0.0, 0.0, 0.0, 4.0),
]


def main():
    meta = json.load(open(os.path.join(B, "voice", "meta.json")))
    lines = {l["id"]: l for l in CFG["lines"]}
    shots, subs, t = [], [], 0.0
    for name, ids, lead, gap, tail, mind in SHOTS:
        st = t; cur = t + lead
        for k, lid in enumerate(ids):
            d = meta[lid]["dur"]
            subs.append(dict(id=lid, speaker=lines[lid]["speaker"], start=round(cur, 3), end=round(cur + d, 3),
                             ml=lines[lid]["text"], en=lines[lid]["en"]))
            cur += d + (gap if k < len(ids) - 1 else 0)
        end = max(st + mind, cur + tail if ids else st + mind)
        shots.append(dict(name=name, start=round(st, 3), end=round(end, 3)))
        t = end
    total = t
    N = int(total * SR)
    V = np.zeros((N, 2))
    for s in subs:
        y, _ = sf.read(os.path.join(B, "voice", s["id"] + ".wav"))
        y = room(y, 0.7, 0.1)   # small dining room
        i = int(s["start"] * SR); seg = y[:N - i]
        pan = {"amma": -0.12, "achan": 0.1, "meera": 0.0, "appu": 0.15}[s["speaker"]]
        V[i:i + len(seg), 0] += seg * (1 - pan); V[i:i + len(seg), 1] += seg * (1 + pan)
    # ambience: crickets all through, wall clock, steel plates / spoons while they eat
    amb = np.zeros((N, 2))
    cr = A.crickets(N); amb[:, 0] += cr * 0.8; amb[:, 1] += np.roll(cr, 2400) * 0.8
    amb += (A.lp(A.rng.normal(0, 1, N), 300) * 0.03)[:, None]
    ck = A.clock(N) * 0.35; amb[:, 0] += ck; amb[:, 1] += ck * 0.8
    rng = np.random.default_rng(5)
    eat_end = next(s["start"] for s in shots if s["name"] == "s08_silence")
    tt = shots[1]["start"] + 0.3
    while tt < eat_end:   # steel tumbler / plate clinks, sparse
        k = int(0.25 * SR); i = int(tt * SR)
        f = rng.uniform(1800, 3400); x = np.arange(k) / SR
        clink = (np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 2.76 * x)) * np.exp(-x * 28) * rng.uniform(0.04, 0.09)
        if i + k < N: amb[i:i + k, 0] += clink * (1 + rng.uniform(-0.5, 0.5)); amb[i:i + k, 1] += clink
        tt += rng.exponential(1.6) + 0.5
    # score: silent at first, a low drone enters at the silence and swells into the father's last line
    mus_l = np.zeros(N + SR * 4); mus_r = np.zeros(N + SR * 4)
    s8 = next(s for s in shots if s["name"] == "s08_silence")["start"]
    s13 = next(s for s in shots if s["name"] == "s13_achan")["start"]
    s15 = next(s for s in shots if s["name"] == "s15_achan")
    M.add(mus_l, M.pad([M.hz("A2"), M.hz("E3"), M.hz("C4")], s13 - s8, vel=0.12, att=2.0, bright=900), s8)
    M.add(mus_r, M.pad([M.hz("A2"), M.hz("E3"), M.hz("C4")], s13 - s8, vel=0.12, att=2.0, bright=900), s8)
    M.add(mus_l, M.pad([M.hz("F2"), M.hz("C3"), M.hz("G#3"), M.hz("C4")], total - s13, vel=0.16, att=3.0, bright=1100), s13)
    M.add(mus_r, M.pad([M.hz("F2"), M.hz("C3"), M.hz("G#3"), M.hz("C4")], total - s13, vel=0.16, att=3.0, bright=1100), s13)
    hit = s15["start"] + 0.6 + meta["l12"]["dur"] + 0.15
    for nm, dt in (("A1", 0.0), ("A2", 0.0), ("E5", 0.6), ("C5", 1.3)):
        x = M.piano(M.hz(nm), 2.5, 0.35 if nm[1] in "12" else 0.12)
        M.add(mus_l, x, hit + dt); M.add(mus_r, x, hit + dt)
    mus = np.stack([M.reverb(mus_l), M.reverb(mus_r)], 1)[:N]
    vl = 20 * np.log10(np.sqrt(np.mean(V[np.abs(V[:, 0]) > 1e-3] ** 2)) + 1e-9)
    def gain_to(x, below):
        l = 20 * np.log10(np.sqrt(np.mean(x[np.abs(x[:, 0]) > 1e-4] ** 2)) + 1e-9)
        return 10 ** ((vl - l - below) / 20)
    mix = V + amb * gain_to(amb, 24) + mus * gain_to(mus, 14)
    fo = int(2.5 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    raw = os.path.join(B, "episode_raw.wav"); sf.write(raw, mix.astype(np.float32), SR)
    out = os.path.join(B, "episode_audio.wav")
    os.system(f'ffmpeg -y -loglevel error -i "{raw}" -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 "{out}"')
    LABELS = {n: f"SHOT {i + 1} - {n.split('_', 1)[1].upper()}" for i, (n, *_r) in enumerate(SHOTS)}
    for s in shots:
        s["label"] = LABELS[s["name"]]
    spec = dict(title=CFG["title_ml"], subtitle=CFG["title_en"], audio=os.path.relpath(out, ROOT), total=round(total, 3),
                shots=shots, subs=subs,
                cards=[dict(text=CFG["title_ml"], sub=CFG["title_en"], start=0.6, end=4.2),
                       dict(text="തുടരും...", sub="TO BE CONTINUED", start=shots[-1]["start"] + 0.4, end=total)])
    json.dump(spec, open(os.path.join(HERE, "spec.json"), "w"), ensure_ascii=False, indent=1)
    print("total", round(total, 2), "s")
    for s in shots:
        print(f'  {s["name"]:12s} {s["start"]:6.2f} - {s["end"]:6.2f}  ({s["end"] - s["start"]:.2f}s)')


if __name__ == "__main__":
    main()
