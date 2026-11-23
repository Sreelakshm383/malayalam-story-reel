"""Lay the story's shot list out against the generated voice lengths.
writes build/<story>/timeline.json   (usage: REEL_STORY=... python3 film2d/timeline.py)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reel import CFG, B

FPS = 30


def timeline():
    meta = json.load(open(os.path.join(B, "voice", "meta.json")))
    out, frame = [], 0
    for name, mind, lines, tail, scene in CFG["shots"]:
        cues, end = [], 0.0
        for lid, st in lines:
            if isinstance(st, str):
                st = end + float(st)
            cues.append(dict(id=lid, start=st, dur=meta[lid]["dur"], speaker=meta[lid]["speaker"], text=meta[lid]["text"]))
            end = st + meta[lid]["dur"]
        n = int(round(max(mind, end + tail) * FPS))
        out.append(dict(name=name, start=frame, frames=n, scene=scene, cues=cues))
        frame += n
    return out


if __name__ == "__main__":
    tl = timeline()
    json.dump(tl, open(os.path.join(B, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("TOTAL", round(sum(s["frames"] for s in tl) / FPS, 2), "s,", len(tl), "shots")
