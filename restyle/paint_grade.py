"""Restyle a clip to the warm, painterly reference-reel look.

Usage: python paint_grade.py input.mp4 output.mp4
Keeps the original audio (voice) and any burned-in text.
Output: 1280x720, 30fps, blurred-fill sides, golden-green grade, painted texture.
"""
import subprocess, sys, json
import numpy as np, cv2

W, H = 1280, 720

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

def paint(img):
    keep = text_mask(img)
    p = cv2.bilateralFilter(img, 7, 40, 7)
    p = cv2.xphoto.oilPainting(p, 4, 12, cv2.COLOR_BGR2Lab)
    p = cv2.bilateralFilter(p, 5, 30, 5)
    # saturation boost (painted Kerala greens/golds); also tints B&W shots warm
    hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.45 + 12, 0, 255)
    p = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    b, g, r = cv2.split(p)
    p = cv2.merge([cv2.LUT(b, LUT_B), cv2.LUT(g, LUT_G), cv2.LUT(r, LUT_R)])
    # soft bloom
    glow = cv2.GaussianBlur(p, (0, 0), 9)
    p = cv2.addWeighted(p, 0.9, glow, 0.14, 0)
    return (p.astype(np.float32) * (1 - keep) + img.astype(np.float32) * keep).astype(np.uint8)

def frame(img, vign):
    h, w = img.shape[:2]
    fh = H; fw = int(round(w * H / h)) // 2 * 2
    fg = cv2.resize(img, (fw, fh), interpolation=cv2.INTER_LANCZOS4)
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
    return (out.astype(np.float32) * vign).astype(np.uint8)

def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return np.clip(1.05 - 0.28 * d ** 2, 0.6, 1)[..., None]

def main(src, dst):
    w, h, fps = probe(src)
    vign = vignette()
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-vf", "noise=alls=4:allf=t",  # light film grain
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", dst], stdin=subprocess.PIPE)
    n = 0
    while True:
        buf = dec.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        enc.stdin.write(frame(img, vign).tobytes())
        n += 1
        if n % 100 == 0:
            print(n, "frames", flush=True)
    enc.stdin.close(); enc.wait(); dec.wait()
    print("done", n, "frames ->", dst)

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--still":
        img = cv2.imread(sys.argv[2]); cv2.imwrite(sys.argv[3], frame(img, vignette()))
    else:
        main(sys.argv[1], sys.argv[2])
