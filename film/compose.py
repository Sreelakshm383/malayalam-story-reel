"""Final compositor: upscale rendered frames to 1080x1920, colour grade, bloom,
vignette, atmosphere particles (dust motes, sparkles, rain), scene dissolves,
title cards and word-by-word highlighted Malayalam + English subtitles; muxes
with the mixed audio to an Instagram-ready H.264 MP4.

usage: python3 film/compose.py [out.mp4] [--from SEC] [--to SEC] [--workers N]
"""
import json, os, sys, math, re, subprocess, argparse
from multiprocessing import Pool
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "film2d"))
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
W, H, FPS = 1080, 1920, 30
ML_FONT = "/usr/share/fonts/opentype/malayalam/Manjari-Bold.otf"
EN_FONT = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
EN_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"

EN = {
    "s1_child": "Amma... let's go quickly! I want to see Grandpa and Grandma!",
    "s1_gma": "My child is here! Come, my dear...",
    "s1_gpa": "So, what's new? What shall we play this time?",
    "s2_gma1": "Come, my boy... Grandma will feed you rice.",
    "s2_child": "I love it when you feed me with your own hands, Grandma!",
    "s2_gma2": "Does my little one want some more?",
    "s3_child1": "Grandpa, can we go to the shop today too?",
    "s3_gpa": "Of course we can... what would my child like?",
    "s3_child2": "Nothing... I just want to go with you, Grandpa!",
    "s4_child1": "Grandma... will you tell me a new story tonight?",
    "s4_gma1": "Once upon a time, there lived a little prince...",
    "s4_child2": "And then? And then?",
    "s4_gma2": "I'll tell you the rest tomorrow. Now sleep, my child.",
    "s5_adult": "How quickly everything changed...",
    "s5_narr": "Back then, we never knew how precious every moment with them was.",
    "s6_narr1": "Today, the house, the courtyard, the old easy chair are all still there...",
    "s6_narr2": "But those old voices, those loving calls...",
    "s6_narr3": "have become memories we can never hear again.",
    "s6_final": "In childhood we had a heaven... it was Grandpa and Grandma's home.",
}

# grading per scene: (warmth, saturation, contrast, lift, vignette, bloom)
GRADE = {0: (1.0, 1.02, 1.02, 0.015, 0.32, 0.12), 1: (1.0, 1.03, 1.02, 0.01, 0.3, 0.12), 2: (1.03, 1.02, 1.03, 0.015, 0.36, 0.18),
         3: (1.0, 1.03, 1.02, 0.01, 0.3, 0.12), 4: (0.95, 1.0, 1.04, 0.0, 0.45, 0.14), 5: (1.05, 0.9, 1.0, 0.03, 0.4, 0.18),
         6: (1.06, 0.88, 1.0, 0.035, 0.4, 0.2)}
ATMOS = {"title": "pollen", "s1_run": "pollen", "s1_gma": "pollen", "s1_gpa": "pollen", "s1_hug": "pollen",
         "s2_wide": "dust", "s2_child": "dust", "s2_gma": "dust", "s3_walk": "pollen", "s3_two": "pollen", "s3_shop": "pollen",
         "s4_wide": "sparks", "s4_story": "sparks", "s4_eager": "sparks", "s4_sleep": "sparks", "s5_timelapse": "rain",
         "s5_return": "pollen", "s5_face": "dust", "s5_photo": "dust", "s6_veranda": "pollen", "s6_toys": "dust",
         "s6_photo": "dust", "s6_final": "fireflies"}


# ---------------------------------------------------------------- word timing
def chunks(text):
    parts = re.split(r"(\.\.\.|[!?.,])", text)
    out, cur = [], ""
    for p in parts:
        if p in ("...", "!", "?", ".", ","):
            if cur.strip():
                out.append(cur.strip() + p)
            cur = ""
        else:
            cur += p
    if cur.strip():
        out.append(cur.strip())
    return out


def segments(y, sr=48000):
    hop = sr // 100
    e = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2)) for i in range(0, len(y) - hop, hop)])
    on = e > max(0.01, 0.12 * np.percentile(e, 95))
    segs, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]: j += 1
            segs.append([i / 100, j / 100]); i = j
        else:
            i += 1
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 0.16:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [s for s in merged if s[1] - s[0] > 0.05]


_META = None


def word_times(cue):
    """start time of each word. Preferred: the word boundaries the voice service reported (build/voice/meta.json),
    matched to the script's words one for one. Fallback: chunks mapped onto detected speech segments, words by length."""
    global _META
    if _META is None:
        _META = json.load(open(os.path.join(B, "voice", "meta.json"), encoding="utf-8"))
    toks, svc = cue["text"].split(), _META.get(cue["id"], {}).get("words") or []
    if len(svc) == len(toks):
        ts = [min(max(0.0, float(t)), cue["dur"] - 0.05) for _, t in svc]
        for i in range(1, len(ts)): ts[i] = max(ts[i], ts[i - 1])
        return list(zip(toks, ts))
    y, sr = sf.read(os.path.join(B, "voice", cue["id"] + ".wav"))
    ch = chunks(cue["text"])
    segs = segments(y, sr)
    if len(segs) != len(ch):
        a0, b0 = (segs[0][0], segs[-1][1]) if segs else (0.0, cue["dur"])
        tot = sum(len(x) for x in ch); acc = 0; segs = []
        for c in ch:
            segs.append((a0 + (b0 - a0) * acc / tot, a0 + (b0 - a0) * (acc + len(c)) / tot)); acc += len(c)
    words = []
    for (a, b), c in zip(segs, ch):
        ws = c.split(); L = sum(len(w) for w in ws); acc = 0
        for w in ws:
            words.append((w, a + (b - a) * acc / L)); acc += len(w)
    return words


# ---------------------------------------------------------------- text drawing
_fonts = {}
def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[k]


def layout(words, fnt, maxw):
    sp = fnt.getlength(" ")
    lines, cur, w = [], [], 0
    for i, wd in enumerate(words):
        lw = fnt.getlength(wd)
        if cur and w + sp + lw > maxw:
            lines.append(cur); cur, w = [], 0
        cur.append((i, wd, lw)); w += (sp if len(cur) > 1 else 0) + lw
    if cur: lines.append(cur)
    # balance two lines
    if len(lines) == 2 and len(lines[1]) < len(lines[0]) // 2 and len(lines[0]) > 2:
        mv = lines[0].pop(); lines[1].insert(0, mv)
    return lines, sp


def draw_block(img, words, nlit, fnt, y, maxw=880, lh=1.35, dim=110, color=(255, 255, 255), shadow=True):
    """draw words centred from y; first nlit words bright, rest dim. returns next y"""
    lines, sp = layout(words, fnt, maxw)
    size = fnt.size
    txt = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    yy = y
    for ln in lines:
        tw = sum(x[2] for x in ln) + sp * (len(ln) - 1)
        x = (W - tw) / 2
        for (i, wd, lw) in ln:
            a = 255 if i < nlit else dim
            d.text((x, yy), wd, font=fnt, fill=(*color, a))
            x += lw + sp
        yy += size * lh
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        a = txt.split()[3].point(lambda v: min(255, int(v * 0.85)))
        sh.putalpha(a.filter(ImageFilter.GaussianBlur(6)))
        sh2 = Image.new("RGBA", img.size, (0, 0, 0, 0)); sh2.paste((10, 6, 4, 255), (0, 0, W, H)); sh2.putalpha(sh.split()[3])
        img.alpha_composite(sh2, (0, 3))
    img.alpha_composite(txt)
    return yy


SUB_TOP, SUB_BOTTOM = 1290, 1580   # Reels-safe subtitle zone (bottom ~340 px is covered by caption/UI)
_sub_cache = {}
def subtitle_layer(cue, t_local):
    """RGBA overlay for a cue at time since cue start"""
    ws = cue["_words"]
    nlit = sum(1 for (_, st) in ws if st <= t_local + 0.05)
    en = EN[cue["id"]].split()
    frac = nlit / len(ws)
    nen = int(round(frac * len(en)))
    key = (cue["id"], nlit)
    if key in _sub_cache: return _sub_cache[key]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fml, fen = font(ML_FONT, 56), font(EN_FONT, 33)
    nml = len(layout([w for w, _ in ws], fml, 900)[0]); nen_l = len(layout(en, fen, 880)[0])
    height = nml * 56 * 1.42 + 8 + nen_l * 33 * 1.4
    top = min(SUB_TOP, SUB_BOTTOM - height)          # long lines grow upward, never into the Reels UI
    y = draw_block(img, [w for w, _ in ws], nlit, fml, top, maxw=900, lh=1.42)
    draw_block(img, en, nen, fen, y + 8, maxw=880, lh=1.4, dim=95, color=(246, 238, 224))
    arr = np.asarray(img).astype(np.float32) / 255.0
    _sub_cache[key] = arr
    return arr


_title_cache = {}
def title_layer(kind):
    if kind in _title_cache: return _title_cache[kind]
    st = json.load(open(os.path.join(ROOT, "story.json")))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    y0 = 250 if kind == "open" else 760
    fml = font(ML_FONT, 66 if kind == "open" else 74)
    t1 = "മുത്തശ്ശന്റെയും"; t2 = "മുത്തശ്ശിയുടെയും വീട്"
    for i, t in enumerate((t1, t2)):
        w = fml.getlength(t)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        ds.text(((W - w) / 2, y0 + i * fml.size * 1.3 + 3), t, font=fml, fill=(20, 10, 4, 200))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
        d.text(((W - w) / 2, y0 + i * fml.size * 1.3), t, font=fml, fill=(255, 236, 196, 255))
    fe = font(EN_BOLD, 30)
    en = st["title_en"]
    spaced = " ".join(en)  # letter-spaced small caps look
    en_s = en.replace(" ", "   ")
    w = fe.getlength(en_s)
    y = y0 + fml.size * 2.75
    d.line(((W - w) / 2, y - 14, (W + w) / 2, y - 14), fill=(255, 220, 160, 160), width=2)
    d.text(((W - w) / 2, y), en_s, font=fe, fill=(255, 244, 228, 235))
    arr = np.asarray(img).astype(np.float32) / 255.0
    _title_cache[kind] = arr
    return arr


# ---------------------------------------------------------------- atmosphere
def sprite(r):
    k = int(r * 4) | 1
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    return np.exp(-(xx ** 2 + yy ** 2) / (2 * r * r)).astype(np.float32)


SPR = {r: sprite(r) for r in (1.5, 2.5, 4, 6, 9)}
def particles(img, kind, name, t, strength=1.0):
    rng = np.random.default_rng(abs(hash(name)) % 2 ** 31)
    if kind == "rain":
        a = np.zeros((H // 2, W // 2), np.float32)
        r2 = np.random.default_rng(int(t * 30))
        storm = math.sin(math.pi * min(1, max(0, (t / 5.5 - 0.2) / 0.6)))
        n = int(500 * storm)
        xs = r2.uniform(0, W // 2, n).astype(int); ys = r2.uniform(0, H // 2, n).astype(int)
        L = r2.integers(10, 26, n)
        for x, y, l in zip(xs, ys, L):
            y1 = min(H // 2, y + l); x1 = min(W // 2 - 1, x + l // 5)
            a[y:y1, x:x1 + 1] += 0.18
        a = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
        img += a[..., None] * np.array([0.75, 0.8, 0.85], np.float32) * 0.6
        return
    cfg = dict(pollen=(28, (1.0, 0.92, 0.72), (1.5, 4), 0.35, 14),
               dust=(45, (1.0, 0.9, 0.7), (1.5, 2.5), 0.28, 8),
               sparks=(18, (1.0, 0.75, 0.35), (2.5, 4), 0.5, 10),
               fireflies=(26, (0.85, 1.0, 0.5), (2.5, 4), 0.9, 18))[kind]
    n, col, rr, amp, speed = cfg
    for i in range(n):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        vx, vy = rng.uniform(-1, 1) * speed, rng.uniform(-1.2, 0.4) * speed
        ph = rng.uniform(0, 6.28); r = rr[0] if rng.random() < 0.6 else rr[1]
        if kind == "fireflies":
            y0 = rng.uniform(H * 0.35, H * 0.8)
        x = (x0 + vx * t + 25 * math.sin(t * 0.7 + ph)) % W
        y = (y0 + vy * t + 18 * math.sin(t * 0.5 + ph * 2)) % H
        tw = (0.5 + 0.5 * math.sin(t * (2.5 if kind in ("fireflies", "sparks") else 1.2) + ph)) ** 2
        s = SPR[r] if r in SPR else SPR[2.5]
        k = s.shape[0] // 2
        xi, yi = int(x), int(y)
        if k < xi < W - k - 1 and k < yi < H - k - 1:
            img[yi - k:yi + k + 1, xi - k:xi + k + 1] += s[..., None] * np.array(col, np.float32) * amp * tw * strength
            if kind in ("fireflies", "sparks"):
                g = SPR[9]; kg = g.shape[0] // 2
                if kg < xi < W - kg - 1 and kg < yi < H - kg - 1:
                    img[yi - kg:yi + kg + 1, xi - kg:xi + kg + 1] += g[..., None] * np.array(col, np.float32) * 0.12 * tw * strength


# ---------------------------------------------------------------- grade
_vig = None
def vignette():
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.47) / (H * 0.6)) ** 2)
        _vig = np.clip(d, 0, 1.4)
    return _vig


def grade(img, scene, warmth_shift=0.0):
    warm, sat, con, lift, vig, bloom = GRADE[scene]
    warm += warmth_shift
    # bloom
    small = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((W // 6, H // 6), Image.BILINEAR)
    sa = np.asarray(small).astype(np.float32) / 255
    hi = np.clip(sa - 0.62, 0, 1) * 2.0
    hb = np.asarray(Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    img = img + hb * bloom * np.array([1.0, 0.85, 0.65], np.float32)
    # white balance / warmth
    img = img * np.array([1 + 0.05 * (warm - 1) * 10 * 0.1 + 0.03, 1.0, 1 - 0.06 - 0.05 * (warm - 1) * 10 * 0.1], np.float32)
    # saturation
    l = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    img = l[..., None] + (img - l[..., None]) * sat
    # filmic contrast around mid grey + warm lifted blacks
    img = np.clip(img, 0, None)
    img = 0.5 + (img - 0.5) * con
    img = img * (1 - lift) + lift * np.array([1.0, 0.82, 0.62], np.float32)
    v = vignette()
    img = img * (1 - vig * np.clip(v - 0.35, 0, 1) ** 1.6)[..., None]
    return img


# ---------------------------------------------------------------- frames
TL = json.load(open(os.path.join(B, "timeline.json")))
TOTAL = sum(s["frames"] for s in TL)
for s in TL:
    for c in s["cues"]:
        c["_words"] = word_times(c)


def shot_at(F):
    for i, s in enumerate(TL):
        if s["start"] <= F < s["start"] + s["frames"]:
            return i, F - s["start"]
    return len(TL) - 1, TL[-1]["frames"] - 1


def load(name, f):
    import shots2d, draw
    return draw.to_array(shots2d.frame(name, f)).copy()


_y = np.arange(H, dtype=np.float32)
BAND = (0.5 * np.clip(1 - np.abs(_y - 1440) / 260, 0, 1) ** 0.8).reshape(H, 1)
DISSOLVE = {"s2_wide": 15, "s3_walk": 15, "s4_wide": 18, "s5_timelapse": 36, "s5_return": 15, "s6_veranda": 18, "s5_face": 12}


def render_frame(F):
    i, f = shot_at(F)
    s = TL[i]; t = f / FPS
    img = load(s["name"], f)
    img = grade(img, s["scene"])
    particles(img, ATMOS[s["name"]], s["name"], t)
    dn = DISSOLVE.get(s["name"], 0)
    if dn and f < dn and i > 0:
        p = TL[i - 1]
        prev = load(p["name"], p["frames"] - 1)
        prev = grade(prev, p["scene"])
        particles(prev, ATMOS[p["name"]], p["name"], (p["frames"] - 1) / FPS)
        a = (f + 1) / (dn + 1); a = a * a * (3 - 2 * a)
        img = prev * (1 - a) + img * a
    # fades
    if F < 18:
        img *= F / 18
    if F > TOTAL - 45:
        img *= max(0, (TOTAL - F) / 45)
    img = np.clip(img, 0, 1)
    # titles
    T = F / FPS
    if T < 5.2:
        a = min(1, max(0, (T - 0.6) / 0.8)) * min(1, max(0, (5.0 - T) / 0.6))
        if a > 0:
            L = title_layer("open"); img = img * (1 - L[..., 3:] * a) + L[..., :3] * L[..., 3:] * a
    fin = TL[-1]
    endT = (fin["start"] + fin["frames"]) / FPS
    if T > endT - 4.6:
        a = min(1, (T - (endT - 4.6)) / 1.0)
        L = title_layer("end"); img = img * (1 - L[..., 3:] * a) + L[..., :3] * L[..., 3:] * a
    # subtitles (fade in/out quickly) over a soft dark band for readability
    band = 0.0
    for c in s["cues"]:
        tl = t - c["start"]
        if -0.3 <= tl <= c["dur"] + 0.5:
            band = max(band, min(1, (tl + 0.3) / 0.3) * min(1, (c["dur"] + 0.5 - tl) / 0.3))
    if band > 0:
        img = img * (1 - band * BAND[..., None])
    for c in s["cues"]:
        tl = t - c["start"]
        if -0.15 <= tl <= c["dur"] + 0.35:
            a = min(1, (tl + 0.15) / 0.15) * min(1, (c["dur"] + 0.35 - tl) / 0.2)
            L = subtitle_layer(c, tl)
            img = img * (1 - L[..., 3:] * a) + L[..., :3] * L[..., 3:] * a
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()


def encode_segment(f0, f1, path):
    """encode frames [f0, f1) to a video-only segment (single process, resumable)"""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
           "-g", "60", "-bf", "2", "-an", path + ".tmp.mp4"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for F in range(f0, f1):
        p.stdin.write(render_frame(F))
    p.stdin.close(); p.wait()
    os.replace(path + ".tmp.mp4", path)


def run_segments(out, nseg=8, workers=4):
    """render the film as nseg independent segments in parallel processes, then concat + mux audio"""
    segdir = os.path.join(B, "segments"); os.makedirs(segdir, exist_ok=True)
    bounds = [round(TOTAL * k / nseg) for k in range(nseg + 1)]
    jobs = []
    for k in range(nseg):
        path = os.path.join(segdir, f"seg{k:02d}.mp4")
        if not os.path.exists(path):
            jobs.append([sys.executable, os.path.abspath(__file__), "--segment", str(bounds[k]), str(bounds[k + 1]), path])
    running = []
    while jobs or running:
        while jobs and len(running) < workers:
            running.append(subprocess.Popen(jobs.pop(0)))
        for r in list(running):
            if r.poll() is not None:
                if r.returncode != 0:
                    raise SystemExit(f"segment failed: {r.args}")
                running.remove(r); print("segment done", r.args[-1], flush=True)
        import time; time.sleep(1)
    lst = os.path.join(segdir, "list.txt")
    with open(lst, "w") as fh:
        for k in range(nseg):
            fh.write(f"file 'seg{k:02d}.mp4'\n")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(B, "mix_norm.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", out], check=True)
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=os.path.join(ROOT, "output", "A_Home_Called_Grandma_and_Grandpa.mp4"))
    ap.add_argument("--from", dest="fr", type=float, default=0); ap.add_argument("--to", type=float, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--still", type=float, default=None)
    ap.add_argument("--segment", nargs=3, default=None)
    ap.add_argument("--pipe", action="store_true", help="old single-pipe multiprocessing path")
    a = ap.parse_args()
    if a.segment:
        encode_segment(int(a.segment[0]), int(a.segment[1]), a.segment[2]); return
    if a.still is not None:
        F = int(a.still * FPS)
        Image.frombytes("RGB", (W, H), render_frame(F)).save(a.out); return
    if not a.pipe and a.to is None and a.fr == 0:
        run_segments(a.out, workers=a.workers); return
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    f0 = int(a.fr * FPS); f1 = TOTAL if a.to is None else int(a.to * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", f"{f0 / FPS}", "-t", f"{(f1 - f0) / FPS}", "-i", os.path.join(B, "mix_norm.wav"),
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", "60", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(a.workers) as pool:
        for k, buf in enumerate(pool.imap(render_frame, range(f0, f1), chunksize=4)):
            p.stdin.write(buf)
            if k % 150 == 0: print("frame", f0 + k, "/", f1, flush=True)
    p.stdin.close(); p.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
