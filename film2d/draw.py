"""Small cairo helpers: colours, gradients, smooth paths, soft shadows,
and the anime cel pass (flat tone bands + ink outlines) for characters."""
import math, os, sys
import cairo
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import maximum_filter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reel import ANIME

W, H = 1080, 1920


def rgb(h, a=1.0):
    if not isinstance(h, str):
        return tuple(h) if len(h) == 4 else (*h, a)
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix(c1, c2, t):
    a, b = rgb(c1) if isinstance(c1, str) else c1, rgb(c2) if isinstance(c2, str) else c2
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def shade(c, k):
    """k<0 darker, k>0 lighter"""
    c = rgb(c) if isinstance(c, str) else c
    if k < 0:
        return (c[0] * (1 + k), c[1] * (1 + k), c[2] * (1 + k), c[3])
    return (c[0] + (1 - c[0]) * k, c[1] + (1 - c[1]) * k, c[2] + (1 - c[2]) * k, c[3])


def col(cr, c):
    c = rgb(c) if isinstance(c, str) else c
    cr.set_source_rgba(*c)


def lin(cr, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for p, c in stops:
        g.add_color_stop_rgba(p, *(rgb(c) if isinstance(c, str) else c))
    cr.set_source(g)


def rad(cr, x, y, r0, r1, stops, x1=None, y1=None):
    g = cairo.RadialGradient(x if x1 is None else x1, y if y1 is None else y1, r0, x, y, r1)
    for p, c in stops:
        g.add_color_stop_rgba(p, *(rgb(c) if isinstance(c, str) else c))
    cr.set_source(g)


def ellipse(cr, x, y, rx, ry, rot=0.0):
    cr.save(); cr.translate(x, y); cr.rotate(rot); cr.scale(max(rx, 1e-3), max(ry, 1e-3))
    cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore()


def rrect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0); cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi); cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def smooth(cr, pts, closed=True, tension=0.5):
    """catmull-rom spline through points"""
    n = len(pts)
    if n < 3:
        cr.move_to(*pts[0]); [cr.line_to(*p) for p in pts[1:]]; return
    P = pts if closed else [pts[0]] + list(pts) + [pts[-1]]
    m = len(P)
    rng_ = range(m) if closed else range(1, m - 2)
    first = True
    for i in rng_:
        p0, p1, p2, p3 = P[(i - 1) % m], P[i % m], P[(i + 1) % m], P[(i + 2) % m]
        if first:
            cr.move_to(*p1); first = False
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        cr.curve_to(*c1, *c2, *p2)
    if closed:
        cr.close_path()


def limb(cr, pts, w, c, w2=None):
    """thick round-capped tube through points (arms/legs)"""
    col(cr, c)
    cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if w2 is None or len(pts) == 2 and w2 == w:
        cr.set_line_width(w)
        cr.move_to(*pts[0]); [cr.line_to(*p) for p in pts[1:]]; cr.stroke()
        return
    for i in range(len(pts) - 1):
        cr.set_line_width(w + (w2 - w) * i / max(1, len(pts) - 2))
        cr.move_to(*pts[i]); cr.line_to(*pts[i + 1]); cr.stroke()


def shadow(cr, x, y, rx, ry, a=0.35):
    rad(cr, x, y, 0, 1, [(0, (0.08, 0.04, 0.02, a)), (1, (0.08, 0.04, 0.02, 0))])
    cr.save(); cr.translate(x, y); cr.scale(rx, ry); cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.fill()


def glow(cr, x, y, r, c, a=0.6):
    c = rgb(c) if isinstance(c, str) else c
    rad(cr, x, y, 0, r, [(0, (*c[:3], a)), (0.35, (*c[:3], a * 0.35)), (1, (*c[:3], 0))])
    cr.arc(x, y, r, 0, 2 * math.pi); cr.fill()


def new_surface(w=W, h=H):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(s)
    cr.set_antialias(cairo.ANTIALIAS_BEST)
    return s, cr


def to_array(s):
    """cairo ARGB32 (premultiplied BGRA) -> float RGB array"""
    buf = np.ndarray((s.get_height(), s.get_width(), 4), np.uint8, s.get_data())
    return buf[..., [2, 1, 0]].astype(np.float32) / 255.0


def blurred_surface(s, radius):
    """blur a cairo surface (premultiplied) and return a new cairo surface"""
    w, h = s.get_width(), s.get_height()
    a = np.ndarray((h, w, 4), np.uint8, s.get_data()).copy()
    im = Image.fromarray(a, "RGBA").filter(ImageFilter.GaussianBlur(radius))
    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    np.ndarray((h, w, 4), np.uint8, out.get_data())[:] = np.asarray(im)
    out.mark_dirty()
    return out


def lerp(a, b, t):
    return a + (b - a) * t


def ss(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ anime cel pass
INK = np.array([0.16, 0.09, 0.11], np.float32)


def _smooth_quant(L, step, soft=0.12):
    """snap luminance to flat bands (anti-aliased band edges)"""
    q = L / step
    f = np.floor(q); r = q - f
    k = np.clip((r - (0.5 - soft)) / (2 * soft), 0, 1)
    return (f + k * k * (3 - 2 * k)) * step


def cel(cr, bbox, fn, R):
    """Draw fn(ctx) offscreen for the user-space box bbox=(x0,y0,x1,y1), turn its soft
    gradients into flat anime tone bands, ink the silhouette and the colour borders,
    then paint it back. R is the character's head radius in user units. Returns fn's result."""
    m = cr.get_matrix()
    corners = [cr.user_to_device(x, y) for x in (bbox[0], bbox[2]) for y in (bbox[1], bbox[3])]
    tgt = cr.get_group_target()
    try:
        TW, TH = tgt.get_width(), tgt.get_height()
    except Exception:
        TW, TH = 4096, 4096
    pad = 8
    x0 = max(0, int(math.floor(min(c[0] for c in corners))) - pad); x1 = min(TW, int(math.ceil(max(c[0] for c in corners))) + pad)
    y0 = max(0, int(math.floor(min(c[1] for c in corners))) - pad); y1 = min(TH, int(math.ceil(max(c[1] for c in corners))) + pad)
    w, h = x1 - x0, y1 - y0
    if w <= 2 or h <= 2:
        return fn(cr)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c2 = cairo.Context(surf); c2.set_antialias(cairo.ANTIALIAS_BEST)
    c2.set_matrix(cairo.Matrix(m.xx, m.yx, m.xy, m.yy, m.x0 - x0, m.y0 - y0))
    res = fn(c2)
    surf.flush()
    buf = np.ndarray((h, w, 4), np.uint8, surf.get_data())
    P = buf[..., [2, 1, 0]].astype(np.float32) / 255.0
    A = buf[..., 3].astype(np.float32) / 255.0
    C = P / np.maximum(A, 1e-4)[..., None]
    Rd = R * math.sqrt(abs(m.xx * m.yy - m.xy * m.yx))     # head radius in pixels
    lw = max(1.4, min(7.0, Rd * 0.075))
    # interior ink where flat colour regions meet (computed before banding, so shading bands stay unlined)
    d = np.zeros((h, w), np.float32)
    dx = np.abs(np.diff(C, axis=1)).sum(-1) * np.minimum(A[:, 1:], A[:, :-1])
    dy = np.abs(np.diff(C, axis=0)).sum(-1) * np.minimum(A[1:], A[:-1])
    d[:, 1:] = np.maximum(d[:, 1:], dx); d[1:] = np.maximum(d[1:], dy)
    inner = np.clip((d - 0.16) / 0.22, 0, 1)
    if Rd > 18:
        k = max(1, int(round(lw * 0.45)))
        if k > 1:
            inner = maximum_filter(inner, size=k)
        inner *= 0.7
    else:
        inner *= 0.35
    # flat tone bands + a little extra vividness
    L = C @ np.array([0.299, 0.587, 0.114], np.float32)
    Lq = _smooth_quant(L, 0.085)
    C = C * ((Lq + 0.02) / (L + 0.02))[..., None]
    l2 = (C @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    C = np.clip(l2 + (C - l2) * 1.12, 0, 1)
    C = C * (1 - inner[..., None]) + INK * inner[..., None]
    # silhouette outline
    k = max(2, int(round(lw)))
    Ad = maximum_filter(A, size=k * 2 + 1)
    Ad = np.asarray(Image.fromarray((Ad * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255
    outA = A + Ad * (1 - A)
    outP = C * A[..., None] + INK * (Ad * (1 - A))[..., None]
    o = np.empty((h, w, 4), np.uint8)
    o[..., 0] = np.clip(outP[..., 2] * 255 + 0.5, 0, 255); o[..., 1] = np.clip(outP[..., 1] * 255 + 0.5, 0, 255)
    o[..., 2] = np.clip(outP[..., 0] * 255 + 0.5, 0, 255); o[..., 3] = np.clip(outA * 255 + 0.5, 0, 255)
    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    np.ndarray((h, w, 4), np.uint8, out.get_data())[:] = o
    out.mark_dirty()
    cr.save(); cr.identity_matrix(); cr.set_source_surface(out, x0, y0); cr.paint(); cr.restore()
    return res
