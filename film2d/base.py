"""Shared shot helpers: timeline/voice data for the current story, lip-sync,
blinks, camera moves and cached static backgrounds."""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reel import B, CFG
from draw import W, H, col, new_surface, blurred_surface, lerp, ss

FPS = 30
TL = json.load(open(os.path.join(B, "timeline.json")))
META = json.load(open(os.path.join(B, "voice", "meta.json")))
SHOT = {s["name"]: s for s in TL}


def mouth(shot, who, t):
    for c in shot["cues"]:
        if c["speaker"] == who and c["start"] <= t < c["start"] + c["dur"]:
            env = META[c["id"]]["env"]; k = int((t - c["start"]) * FPS)
            if 0 <= k < len(env):
                return min(1.0, env[k] * (0.8 + 0.2 * math.sin(t * 23)))
    return 0.0


def speaking(shot, who, t, pre=0.3, post=0.2):
    return any(c["speaker"] == who and c["start"] - pre < t < c["start"] + c["dur"] + post for c in shot["cues"])


def cue(shot, lid):
    return next(c for c in shot["cues"] if c["id"] == lid)


def blink(t, seed):
    r = random.Random(seed)
    for k in range(60):
        bt = k * 3.1 + r.uniform(0, 2.4)
        d = t - bt
        if 0 <= d < 0.16:
            return 1 - abs(d - 0.08) / 0.08
    return 0.0


def camera(cr, z, cx, cy):
    cr.translate(W / 2, H / 2); cr.scale(z, z); cr.translate(-cx, -cy)


def cam_lerp(t, dur, a, b):
    u = ss(t / dur)
    return tuple(lerp(a[i], b[i], u) for i in range(3))


_cache = {}
def cached(key, fn, blur=0):
    """static background painted once per shot into a 2x-oversized surface (optionally blurred)"""
    if key not in _cache:
        s, cr = new_surface(W * 2, H * 2)
        cr.translate(W / 2, H / 2)
        fn(cr)
        _cache[key] = blurred_surface(s, blur) if blur else s
    return _cache[key]


def paint_cached(cr, surf):
    cr.save(); cr.translate(-W / 2, -H / 2); cr.set_source_surface(surf, 0, 0); cr.paint(); cr.restore()


def render(funcs, name, f):
    shot = SHOT[name]
    s, cr = new_surface()
    col(cr, "#000000"); cr.paint()
    cr.save()
    funcs[name](cr, f / FPS, shot)
    cr.restore()
    return s
