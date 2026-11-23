"""Style sample for the Yakshi short, Scene 3 ("she did not laugh"): extreme close-up
of the 9-year-old's eyes in the 2D mythic illustrated look (bold ink, painterly
saffron skin, kohl, bindi, gold dust, grain, chromatic fringe).

usage: python3 production/yakshi/sample_eyes.py [out.png]
"""
import math, os, random, sys
import cairo
import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920
INK = (0.09, 0.04, 0.03)
rnd = random.Random(7)


def rgb(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def lin(cr, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for p, c in stops:
        g.add_color_stop_rgba(p, *(rgb(c) if isinstance(c, str) else c))
    cr.set_source(g)


def rad(cr, x, y, r0, r1, stops):
    g = cairo.RadialGradient(x, y, r0, x, y, r1)
    for p, c in stops:
        g.add_color_stop_rgba(p, *(rgb(c) if isinstance(c, str) else c))
    cr.set_source(g)


def taper(cr, pts, w0, w1, c):
    """ink stroke that tapers from w0 to w1 along a polyline"""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[min(i + 1, n - 1)]; b = pts[max(i - 1, 0)]
        dx, dy = a[0] - b[0], a[1] - b[1]; L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = (w0 + (w1 - w0) * i / (n - 1)) / 2
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    cr.move_to(*left[0])
    for p in left[1:]: cr.line_to(*p)
    for p in reversed(right): cr.line_to(*p)
    cr.close_path(); cr.set_source_rgba(*c); cr.fill()


def bez(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return out


def eye(cr, cx, cy, s, side):
    """almond eye; side=-1 (screen left) / +1 (screen right); outer corner is toward the side"""
    w, h = 185 * s, 92 * s
    ox, ix = cx + side * w, cx - side * w * 0.95          # outer / inner corner x
    up = [(ix, cy + 8 * s), (ix + side * w * 0.55, cy - h * 1.05), (ox - side * w * 0.5, cy - h * 1.15), (ox, cy - 14 * s)]
    lo = [(ox, cy - 14 * s), (ox - side * w * 0.45, cy + h * 0.85), (ix + side * w * 0.5, cy + h * 0.8), (ix, cy + 8 * s)]
    def shape():
        cr.move_to(*up[0]); cr.curve_to(*up[1], *up[2], *up[3]); cr.curve_to(*lo[1], *lo[2], *lo[3]); cr.close_path()
    # kohl smudge around the eye
    cr.save(); shape(); cr.set_source_rgba(0.12, 0.05, 0.04, 0.35); cr.set_line_width(46 * s); cr.stroke(); cr.restore()
    # eyelid crease + lid shading
    lin(cr, 0, cy - h * 2.0, 0, cy - h * 0.4, [(0, (0.55, 0.22, 0.08, 0)), (1, (0.35, 0.12, 0.05, 0.45))])
    cr.move_to(ix - side * 10 * s, cy - 10 * s); cr.curve_to(ix + side * w * 0.5, cy - h * 1.9, ox - side * w * 0.4, cy - h * 1.95, ox + side * 30 * s, cy - h * 0.55)
    cr.line_to(ox, cy - 14 * s); cr.curve_to(*up[2], *up[1], *up[0]); cr.close_path(); cr.fill()
    taper(cr, bez((ix + side * w * 0.15, cy - h * 1.05), (ix + side * w * 0.6, cy - h * 1.75), (ox - side * w * 0.35, cy - h * 1.72), (ox + side * 10 * s, cy - h * 0.8)),
          3 * s, 9 * s, (*INK, 0.75))
    # sclera
    cr.save(); shape(); cr.clip()
    lin(cr, 0, cy - h, 0, cy + h, [(0, "#b8987a"), (0.4, "#ead6bb"), (1, "#cfb393")]); cr.paint()
    # iris: deep brown-black with a blue rim glow (like the reference eyes)
    irx, iry = 84 * s, 88 * s
    icx, icy = cx - side * 6 * s, cy + 6 * s
    rad(cr, icx, icy, 0, irx, [(0, "#0c0503"), (0.5, "#22100a"), (0.84, "#4a2812"), (0.94, "#35509a"), (1, "#08080f")])
    cr.arc(icx, icy, irx, 0, 2 * math.pi); cr.fill()
    for k in range(40):   # iris fibres
        a = k / 40 * 2 * math.pi
        cr.set_source_rgba(0.55, 0.32, 0.18, 0.22); cr.set_line_width(2 * s)
        cr.move_to(icx + math.cos(a) * irx * 0.42, icy + math.sin(a) * iry * 0.42)
        cr.line_to(icx + math.cos(a + 0.05) * irx * 0.8, icy + math.sin(a + 0.05) * iry * 0.8); cr.stroke()
    cr.set_source_rgba(0.02, 0.01, 0.01, 1); cr.arc(icx, icy, irx * 0.4, 0, 2 * math.pi); cr.fill()
    # reflection of the bright window with tiny laughing classmates in silhouette
    wx, wy = icx - irx * 0.5, icy - iry * 0.62
    rad(cr, wx + irx * 0.3, wy + iry * 0.15, 0, irx * 0.45, [(0, (1, 0.9, 0.7, 0.4)), (1, (1, 0.9, 0.7, 0))])
    cr.arc(wx + irx * 0.3, wy + iry * 0.15, irx * 0.45, 0, 2 * math.pi); cr.fill()
    cr.set_source_rgba(0.08, 0.04, 0.03, 0.55)
    for k in range(5):   # tiny laughing classmates mirrored in her eye
        hx = wx + irx * (0.05 + k * 0.11) + rnd.uniform(-2, 2); hy = wy + iry * 0.26 + rnd.uniform(-2, 2)
        cr.arc(hx, hy - 3 * s, 3.5 * s, 0, 2 * math.pi); cr.fill()
        cr.move_to(hx - 4 * s, hy + 8 * s); cr.line_to(hx, hy); cr.line_to(hx + 4 * s, hy + 8 * s); cr.close_path(); cr.fill()
    # catchlights
    cr.set_source_rgba(1, 1, 1, 0.95); cr.arc(icx + side * irx * 0.4, icy - iry * 0.34, 11 * s, 0, 2 * math.pi); cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.6); cr.arc(icx - side * irx * 0.3, icy + iry * 0.45, 6 * s, 0, 2 * math.pi); cr.fill()
    # upper-lid shadow on the eyeball
    lin(cr, 0, cy - h, 0, cy - h * 0.1, [(0, (0.15, 0.05, 0.03, 0.75)), (1, (0.15, 0.05, 0.03, 0))]); cr.paint()
    cr.restore()
    # heavy upper lash line with a kohl wing
    upl = bez(*up)
    taper(cr, upl, 8 * s, 32 * s, (*INK, 1))
    wing = bez((ox - side * 5 * s, cy - 16 * s), (ox + side * 40 * s, cy - 30 * s), (ox + side * 75 * s, cy - 50 * s), (ox + side * 110 * s, cy - 78 * s), 20)
    taper(cr, wing, 22 * s, 2 * s, (*INK, 1))
    for k in range(14):   # lashes
        t = 0.3 + 0.7 * k / 13
        px, py = upl[int(t * (len(upl) - 1))]
        ang = -math.pi / 2 + side * (0.25 + 0.9 * t)
        L = (18 + 30 * t) * s
        lash = bez((px, py), (px + math.cos(ang) * L * 0.3, py + math.sin(ang) * L * 0.5),
                   (px + math.cos(ang) * L * 0.8, py + math.sin(ang) * L * 0.9), (px + math.cos(ang + side * 0.5) * L, py + math.sin(ang + side * 0.5) * L), 10)
        taper(cr, lash, 5 * s, 0.6 * s, (*INK, 1))
    # lower lid: kohl line (waterline) thick at outer half
    lol = bez(*lo)
    taper(cr, lol, 12 * s, 3 * s, (*INK, 0.9))


def brow(cr, cx, cy, s, side):
    inner = (cx - side * 165 * s, cy + 28 * s)
    pts = bez(inner, (cx - side * 60 * s, cy - 45 * s), (cx + side * 110 * s, cy - 60 * s), (cx + side * 245 * s, cy + 20 * s))
    taper(cr, pts, 44 * s, 6 * s, (0.1, 0.05, 0.04, 1))
    for k in range(70):   # painted hair strokes
        t = k / 69
        px, py = pts[int(t * (len(pts) - 1))]
        px += rnd.uniform(-8, 8) * s; py += rnd.uniform(-14, 10) * s * (1 - t * 0.6)
        ang = -0.5 * side + side * t * 0.9 + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(18, 34) * s
        cr.set_source_rgba(0.06, 0.03, 0.02, 0.8); cr.set_line_width(rnd.uniform(1.5, 3.5) * s)
        cr.move_to(px, py); cr.line_to(px + side * math.cos(ang) * L, py - abs(math.sin(ang)) * L * 0.5); cr.stroke()


def main(out):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(s); cr.set_antialias(cairo.ANTIALIAS_BEST)
    # skin: saffron-lit dusky skin, light from the classroom window (screen right)
    lin(cr, 0, 0, W, 0, [(0, "#6a2a10"), (0.35, "#b5531f"), (0.7, "#d97a32"), (1, "#f0a050")]); cr.paint()
    rad(cr, 900, 700, 50, 900, [(0, (1, 0.78, 0.45, 0.35)), (1, (1, 0.78, 0.45, 0))]); cr.paint()
    lin(cr, 0, 0, 0, H, [(0, (0.15, 0.05, 0.02, 0.55)), (0.25, (0, 0, 0, 0)), (0.75, (0, 0, 0, 0)), (1, (0.12, 0.04, 0.02, 0.7))]); cr.paint()
    # painterly skin texture
    for _ in range(900):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        cr.set_source_rgba(*rnd.choice([(0.45, 0.16, 0.06), (0.95, 0.6, 0.3), (0.7, 0.3, 0.12)]), rnd.uniform(0.03, 0.07))
        cr.save(); cr.translate(x, y); cr.rotate(rnd.uniform(0, 3.14)); cr.scale(rnd.uniform(20, 70), rnd.uniform(6, 18))
        cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.fill()
    # nose bridge shadow down the centre
    for (x, a_) in ((500, (0.3, 0.1, 0.04, 0.22)), (585, (1, 0.82, 0.55, 0.16))):   # soft nose bridge
        cr.save(); cr.translate(x, 1350); cr.scale(55, 600)
        rad(cr, 0, 0, 0, 1, [(0, a_), (1, (*a_[:3], 0))]); cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.fill()
    # nose tip, nostrils and closed, unsmiling lips
    rad(cr, 560, 1330, 0, 120, [(0, (1, 0.8, 0.5, 0.3)), (1, (1, 0.8, 0.5, 0))]); cr.arc(560, 1330, 120, 0, 2 * math.pi); cr.fill()
    for sx in (-1, 1):
        cr.save(); cr.translate(545 + sx * 62, 1420); cr.rotate(sx * 0.35); cr.scale(30, 15)
        cr.set_source_rgba(0.18, 0.06, 0.03, 0.85); cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.fill()
        taper(cr, bez((545 + sx * 40, 1370), (545 + sx * 110, 1360), (545 + sx * 125, 1420), (545 + sx * 95, 1450), 20), 3, 8, (*INK, 0.55))
    taper(cr, bez((470, 1445), (510, 1462), (580, 1462), (620, 1445), 20), 4, 4, (*INK, 0.35))
    lin(cr, 0, 1640, 0, 1760, [(0, "#7a2a1c"), (1, "#a8452c")])
    cr.move_to(395, 1700); cr.curve_to(450, 1655, 510, 1640, 545, 1668); cr.curve_to(580, 1640, 640, 1655, 695, 1700)
    cr.curve_to(640, 1780, 450, 1780, 395, 1700); cr.close_path(); cr.fill()
    cr.set_source_rgba(1, 0.85, 0.65, 0.3); cr.save(); cr.translate(560, 1735); cr.scale(70, 12); cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.fill()
    taper(cr, bez((395, 1700), (470, 1712), (620, 1712), (695, 1700), 30), 7, 5, (*INK, 0.9))
    # hair: oiled black hair at the top with violet sheen, centre parting
    lin(cr, 0, 0, 0, 460, [(0, "#08040a"), (1, "#1a0c14")])
    cr.move_to(0, 0); cr.line_to(W, 0); cr.line_to(W, 400); cr.curve_to(1000, 280, 760, 170, 600, 155)
    cr.curve_to(570, 145, 520, 145, 490, 155); cr.curve_to(330, 170, 80, 280, 0, 400); cr.close_path(); cr.fill()
    for k in range(90):   # baby hairs along the hairline
        t = rnd.uniform(0, 1); side = -1 if t < 0.5 else 1
        x = 545 + side * (abs(t - 0.5) * 2) * 540; y = 150 + (abs(t - 0.5) * 2) ** 1.6 * 245
        cr.set_source_rgba(0.05, 0.02, 0.03, rnd.uniform(0.4, 0.9)); cr.set_line_width(rnd.uniform(1, 2.5))
        cr.move_to(x, y - 8); cr.curve_to(x + rnd.uniform(-10, 10), y + 10, x + side * rnd.uniform(5, 25), y + 20, x + side * rnd.uniform(10, 35), y + rnd.uniform(18, 40)); cr.stroke()
    for k in range(60):   # strands + violet sheen
        side = -1 if k % 2 else 1
        x0 = 545 + side * rnd.uniform(0, 30)
        x1 = 545 + side * rnd.uniform(200, 600)
        cr.set_source_rgba(0.45, 0.3, 0.7, rnd.uniform(0.08, 0.25)); cr.set_line_width(rnd.uniform(1.5, 4))
        cr.move_to(x0, 140); cr.curve_to(x0 + side * 120, 130, x1 - side * 60, 180, x1, 240 + abs(x1 - 545) * 0.25); cr.stroke()
    taper(cr, bez((545, 145), (545, 100), (545, 50), (545, 0), 10), 6, 3, (0.5, 0.18, 0.12, 0.75))   # parting (sindoor-red scalp line)
    # brows, bindi, eyes
    brow(cr, 300, 570, 1.12, -1); brow(cr, 790, 570, 1.12, 1)
    cr.set_source_rgba(0.04, 0.02, 0.02, 1); cr.arc(545, 540, 22, 0, 2 * math.pi); cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.35); cr.arc(539, 533, 5, 0, 2 * math.pi); cr.fill()
    eye(cr, 300, 810, 1.15, -1); eye(cr, 790, 810, 1.15, 1)
    # mole under her left eye (screen right)
    cr.set_source_rgba(0.12, 0.05, 0.03, 0.9); cr.arc(850, 1010, 10, 0, 2 * math.pi); cr.fill()
    # cheek blush and a cool violet rim from the coming night on the shadow side
    rad(cr, 160, 1350, 0, 300, [(0, (0.85, 0.25, 0.2, 0.18)), (1, (0.85, 0.25, 0.2, 0))]); cr.paint()
    lin(cr, 0, 0, 260, 0, [(0, (0.35, 0.2, 0.75, 0.45)), (1, (0.35, 0.2, 0.75, 0))]); cr.paint()
    # light shafts + gold dust
    for k in range(4):
        lin(cr, W, 200, 300, 1700, [(0, (1, 0.85, 0.5, 0.12)), (1, (1, 0.85, 0.5, 0))])
        cr.move_to(W, 150 + k * 260); cr.line_to(W, 260 + k * 260); cr.line_to(200, 1900); cr.line_to(80, 1900); cr.close_path(); cr.fill()
    for _ in range(140):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.2, 4.5)
        rad(cr, x, y, 0, r * 4, [(0, (1, 0.9, 0.55, 0.9)), (0.3, (1, 0.75, 0.3, 0.35)), (1, (1, 0.7, 0.2, 0))])
        cr.arc(x, y, r * 4, 0, 2 * math.pi); cr.fill()
    s.flush()
    a = np.ndarray((H, W, 4), np.uint8, s.get_data())[..., [2, 1, 0]].astype(np.float32) / 255
    # bloom, chromatic fringe, vignette, grain
    im = Image.fromarray((a * 255).astype(np.uint8))
    hi = np.clip(np.asarray(im.resize((W // 6, H // 6))).astype(np.float32) / 255 - 0.6, 0, 1) * 2
    hb = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)).resize((W, H))).astype(np.float32) / 255
    a = a + hb * np.array([0.35, 0.25, 0.12], np.float32)
    a[..., 0] = np.roll(a[..., 0], 3, axis=1); a[..., 2] = np.roll(a[..., 2], -3, axis=1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H * 0.5) / (H * 0.62)) ** 2)
    a *= (1 - 0.55 * np.clip(v - 0.45, 0, 1) ** 1.4)[..., None]
    a += np.random.default_rng(3).normal(0, 0.025, (H, W, 1)).astype(np.float32)
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_scene3_eyes.png"))
