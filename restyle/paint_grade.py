"""Restyle a clip to the warm, painterly reference-reel look.

Usage: python paint_grade.py input.mp4 output.mp4
Keeps the original audio (voice) and any burned-in text.
Output: 1280x720, 30fps, blurred-fill sides, golden-green grade, painted texture.
"""
import subprocess, sys, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subtitles as SUB

W, H = 1280, 720
import os
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wm_template.png')

def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", path])
    s = json.loads(out)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d)

def make_luts():
    x = np.arange(256, dtype=np.float32) / 255
    # gentle S-curve with lifted blacks (film/painting feel)
    s = 0.03 + 0.95 * (x - 0.22 * np.sin(2 * np.pi * x) / (2 * np.pi) * 2.2)
    s = np.clip(s, 0, 1)
    b = np.clip(s * 0.86 + 0.02, 0, 1)            # pull blue -> warm
    g = np.clip(s * 1.00 + 0.015 * np.sin(np.pi * x), 0, 1)  # slight green in mids
    r = np.clip(s * 1.06 + 0.02, 0, 1)            # golden highlights
    return [(c * 255).astype(np.uint8) for c in (b, g, r)]

LUT_B, LUT_G, LUT_R = make_luts()

def text_mask(img):
    """Bright, low-saturation thin strokes = burned-in subtitles/text. Keep them crisp."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bright = (hsv[..., 2] > 200) & (hsv[..., 1] < 50)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    m = (bright & (tophat > 40)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2)
    return cv2.GaussianBlur(m, (5, 5), 0).astype(np.float32)[..., None] / 255

# Watermark spots in the source clip (760x576): "@handle" text box (x, y) and the
# fixed top-left channel logo. Matched per frame; only thin bright/coloured strokes
# inside the box are removed, so the picture behind stays intact.
WM_TEXT_POS = [(558, 205), (89, 448)]
WM_TEXT_SIZE = (140, 23)
WM_LOGO_BOX = (4, 12, 152, 35)   # x0, y0, x1, y1
TEMPLATE = None
PAINT_SIZE, PAINT_DYN = 5, 6

def stroke_mask(roi, k=15, thr=28):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    th = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    bright = (th > thr) & (gray > 140)
    colour = (hsv[..., 1] > 110) & (hsv[..., 2] > 130) & ((hsv[..., 0] < 22) | (hsv[..., 0] > 130))
    return ((bright | colour).astype(np.uint8)) * 255

def remove_watermark(img, t=None):
    global TEMPLATE
    img = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = np.zeros(gray.shape, np.uint8)
    tw, th = WM_TEXT_SIZE
    for (x, y) in WM_TEXT_POS:
        roi = gray[y - 6:y + th + 6, x - 6:x + tw + 6]
        if roi.shape[0] < th or roi.shape[1] < tw:
            continue
        score = cv2.matchTemplate(roi, TEMPLATE, cv2.TM_CCOEFF_NORMED).max()
        if score < 0.45:
            continue
        x0, y0, x1, y1 = x - 30, y - 80, x + tw + 30, y + th + 8
        x0, y0 = max(0, x0), max(0, y0)
        mask[y0:y1, x0:x1] |= stroke_mask(img[y0:y1, x0:x1])
    x0, y0, x1, y1 = WM_LOGO_BOX
    mask[y0:y1, x0:x1] |= stroke_mask(img[y0:y1, x0:x1], k=11, thr=20)
    if t is not None:
        for sub in SUB.active(t):
            x0, y0, x1, y1 = SUB.src_box(sub)
            mask[max(0, y0):y1, max(0, x0):x1] = 255
    if mask.any():
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
        img = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
    return img

def paint(img):
    # 1) enhance: denoise + 2x upscale + sharpen
    h, w = img.shape[:2]
    e = cv2.bilateralFilter(img, 5, 18, 5)
    e = cv2.resize(e, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    e = cv2.addWeighted(e, 1.6, cv2.GaussianBlur(e, (0, 0), 2.0), -0.6, 0)
    # 2) painting at 2x: brush strokes stay fine, faces stay clear
    p = cv2.xphoto.oilPainting(e, PAINT_SIZE, PAINT_DYN, cv2.COLOR_BGR2Lab)
    p = cv2.detailEnhance(p, sigma_s=8, sigma_r=0.12)
    p = cv2.resize(p, (w, h), interpolation=cv2.INTER_AREA)
    # saturation boost (painted Kerala greens/golds); also tints B&W shots warm
    hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.45 + 12, 0, 255)
    p = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    b, g, r = cv2.split(p)
    p = cv2.merge([cv2.LUT(b, LUT_B), cv2.LUT(g, LUT_G), cv2.LUT(r, LUT_R)])
    # soft bloom
    glow = cv2.GaussianBlur(p, (0, 0), 9)
    p = cv2.addWeighted(p, 0.9, glow, 0.10, 0)
    return p

def frame(img, vign, t=None):
    h, w = img.shape[:2]
    fh = H; fw = int(round(w * H / h)) // 2 * 2
    fg = cv2.resize(remove_watermark(img, t), (fw, fh), interpolation=cv2.INTER_LANCZOS4)
    fg = paint(fg)
    bg = cv2.resize(fg, (W, int(round(fh * W / fw))))
    y0 = (bg.shape[0] - H) // 2
    bg = cv2.GaussianBlur(bg[y0:y0 + H], (0, 0), 28)
    bg = (bg * 0.7).astype(np.uint8)
    out = bg.copy()
    x0 = (W - fw) // 2
    # feathered edges so the picture melts into the blurred fill
    alpha = np.ones((fh, fw), np.float32)
    f = 40
    ramp = np.linspace(0, 1, f, dtype=np.float32)
    alpha[:, :f] *= ramp; alpha[:, -f:] *= ramp[::-1]
    a = alpha[..., None]
    out[:, x0:x0 + fw] = (fg * a + out[:, x0:x0 + fw] * (1 - a)).astype(np.uint8)
    out = (out.astype(np.float32) * vign).astype(np.uint8)
    if t is not None:
        out = draw_subs(out, t, x0, fh / h)
    return out

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "cormorant-garamond-latin-600-normal.woff")
_FONT_CACHE = {}

def font_size_for(text, width_px):
    f = ImageFont.truetype(FONT_PATH, 100)
    return int(100 * width_px / f.getlength(text))

def sub_font_size(scale):
    # one size for every line, calibrated so lines match the original widths
    sizes = sorted(font_size_for(s[2], s[6] * scale) for s in SUB.SUBS)
    return sizes[len(sizes) // 2]

def draw_subs(frame_bgr, t, x_off, scale):
    subs = SUB.active(t)
    if not subs:
        return frame_bgr
    size = _FONT_CACHE.setdefault(("size", scale), sub_font_size(scale))
    font = _FONT_CACHE.setdefault(size, ImageFont.truetype(FONT_PATH, size))
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    shadow = Image.new("L", img.size, 0)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ds, dl = ImageDraw.Draw(shadow), ImageDraw.Draw(layer)
    for (st, en, text, align, x, cy, w, col) in subs:
        # quick fade in/out (0.15 s)
        a = min(1.0, (t - st) / 0.15, (en - t) / 0.15)
        tw = font.getlength(text)
        X = x * scale + x_off
        X = {"l": X, "c": X - tw / 2, "r": X - tw}[align]
        X = min(max(X, 24), W - 24 - tw)
        Y = cy * scale
        ds.text((X + 2, Y + 3), text, font=font, fill=int(200 * a), anchor="lm")
        dl.text((X, Y), text, font=font, fill=col + (int(255 * a),), anchor="lm")
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    dark = Image.new("RGBA", img.size, (0, 0, 0, 255))
    dark.putalpha(shadow.point(lambda v: v * 0.75))
    img = Image.alpha_composite(img.convert("RGBA"), dark)
    img = Image.alpha_composite(img, layer)
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return np.clip(1.05 - 0.28 * d ** 2, 0.6, 1)[..., None]

import multiprocessing as mp
_W = _H = _V = None

def _init(w, h):
    global _W, _H, _V, TEMPLATE
    _W, _H, _V = w, h, vignette()
    TEMPLATE = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    cv2.setNumThreads(1)

def _work(item):
    t, buf = item
    img = np.frombuffer(buf, np.uint8).reshape(_H, _W, 3)
    return frame(img, _V, t).tobytes()

END_AT = 42.3   # source has a channel end card from 42.37s; cut before it

def main(src, dst):
    global TEMPLATE
    TEMPLATE = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    w, h, fps = probe(src)
    vign = vignette()
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-t", str(END_AT), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-vf", f"noise=alls=2:allf=t,fade=t=out:st={END_AT - 0.8}:d=0.8",  # very light film grain
        "-af", f"afade=t=out:st={END_AT - 1.2}:d=1.2", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", dst], stdin=subprocess.PIPE)
    def frames():
        i = 0
        while True:
            buf = dec.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                return
            yield (i / fps, buf)
            i += 1
    n = 0
    with mp.Pool(os.cpu_count(), initializer=_init, initargs=(w, h)) as pool:
        for out in pool.imap(_work, frames(), chunksize=2):
            enc.stdin.write(out)
            n += 1
            if n % 100 == 0:
                print(n, "frames", flush=True)
    enc.stdin.close(); enc.wait(); dec.wait()
    print("done", n, "frames ->", dst)

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--still":
        TEMPLATE = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
        t = float(sys.argv[4]) if len(sys.argv) > 4 else None
        img = cv2.imread(sys.argv[2]); cv2.imwrite(sys.argv[3], frame(img, vignette(), t))
    else:
        main(sys.argv[1], sys.argv[2])
