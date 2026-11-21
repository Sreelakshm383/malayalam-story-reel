"""Shot list and timeline (no Blender needed). Shot lengths come from the voice durations.

usage: python3 film/timeline.py   -> writes build/timeline.json
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30

# (name, min duration s, [(line_id, start_s)], tail_s, scene)
SHOTS = [
    ("title",          5.0, [], 0, 0),
    ("s1_run",         0.0, [("s1_child", 0.5)], 0.7, 1),
    ("s1_gma",         0.0, [("s1_gma", 0.35)], 0.6, 1),
    ("s1_gpa",         0.0, [("s1_gpa", 0.35)], 0.7, 1),
    ("s1_hug",         3.6, [], 0, 1),
    ("s2_wide",        0.0, [("s2_gma1", 0.7)], 0.6, 2),
    ("s2_child",       0.0, [("s2_child", 1.6)], 0.6, 2),
    ("s2_gma",         0.0, [("s2_gma2", 0.35)], 0.9, 2),
    ("s3_walk",        0.0, [("s3_child1", 1.1), ("s3_gpa", "+0.35")], 0.5, 3),
    ("s3_two",         0.0, [("s3_child2", 0.3)], 0.8, 3),
    ("s3_shop",        3.8, [], 0, 3),
    ("s4_wide",        0.0, [("s4_child1", 0.9)], 0.5, 4),
    ("s4_story",       0.0, [("s4_gma1", 0.3)], 0.5, 4),
    ("s4_eager",       0.0, [("s4_child2", 0.2)], 0.4, 4),
    ("s4_sleep",       0.0, [("s4_gma2", 0.3)], 3.2, 4),
    ("s5_timelapse",   5.5, [], 0, 5),
    ("s5_return",      5.0, [], 0, 5),
    ("s5_face",        0.0, [("s5_adult", 0.9)], 0.7, 5),
    ("s5_photo",       0.0, [("s5_narr", 0.3)], 0.9, 5),
    ("s6_veranda",     0.0, [("s6_narr1", 0.6)], 0.6, 6),
    ("s6_toys",        0.0, [("s6_narr2", 0.3)], 0.5, 6),
    ("s6_photo",       0.0, [("s6_narr3", 0.3)], 0.8, 6),
    ("s6_final",      13.0, [("s6_final", 1.2)], 0, 6),
]


def timeline():
    meta = json.load(open(os.path.join(ROOT, "build", "voice", "meta.json")))
    out, frame = [], 0
    for name, mind, lines, tail, scene in SHOTS:
        cues, end = [], 0.0
        for lid, st in lines:
            if isinstance(st, str):
                st = end + float(st)
            cues.append(dict(id=lid, start=st, dur=meta[lid]["dur"], speaker=meta[lid]["speaker"], text=meta[lid]["text"]))
            end = st + meta[lid]["dur"]
        dur = max(mind, end + tail)
        n = int(round(dur * FPS))
        out.append(dict(name=name, start=frame, frames=n, scene=scene, cues=cues))
        frame += n
    return out, meta



if __name__ == "__main__":
    tl, _ = timeline()
    json.dump(tl, open(os.path.join(ROOT, "build", "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("shots", len(tl), "seconds", sum(s["frames"] for s in tl) / FPS)
