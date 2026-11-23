"""Painted 2D environments (soft illustrated Kerala village style)."""
import math, random
import cairo
from draw import rgb, shade, mix, col, lin, rad, ellipse, rrect, smooth, limb, shadow, glow, ss, ANIME

# ------------------------------------------------------------------ sky
SKIES = {
    "day":   [(0, "#8cbfd8"), (0.55, "#cfe0d8"), (1, "#f6dcaa")],
    "gold":  [(0, "#7fa9c9"), (0.5, "#e9cfa0"), (1, "#f7c27a")],
    "dusk":  [(0, "#3a4677"), (0.45, "#a9708a"), (0.8, "#f0a066"), (1, "#f7c47e")],
    "night": [(0, "#08132a"), (0.6, "#14284a"), (1, "#24406a")],
    "grey":  [(0, "#6f7f8c"), (1, "#b9c2c4")],
    "rain":  [(0, "#4d5d72"), (0.6, "#7f8fa0"), (1, "#a9b4bc")],
}
# anime skies: deeper, more saturated blues and glowing horizons
ANIME_SKIES = {
    "day":   [(0, "#1f6fd6"), (0.5, "#6ab8f2"), (0.85, "#c8ecff"), (1, "#f4fbff")],
    "gold":  [(0, "#2a62c0"), (0.45, "#7fb4e6"), (0.75, "#f6d29a"), (1, "#ffb15e")],
    "dusk":  [(0, "#26246e"), (0.4, "#7a4fa0"), (0.7, "#f07a7a"), (0.9, "#ffb36a"), (1, "#ffe0a0")],
    "night": [(0, "#050b24"), (0.55, "#10265a"), (1, "#2a4f8f")],
    "grey":  [(0, "#5f7286"), (1, "#c2ccd2")],
    "rain":  [(0, "#3e4f6c"), (0.55, "#6f86a3"), (1, "#a6b8c8")],
}


def sky(cr, kind, y0=0, y1=1300, x0=-600, x1=1700, t=0.0, sun=None):
    lin(cr, 0, y0, 0, y1, ((ANIME_SKIES if ANIME else SKIES)[kind]) if isinstance(kind, str) else kind)
    cr.rectangle(x0, y0 - 800, x1 - x0, y1 - y0 + 800); cr.fill()
    if sun:
        sx, sy, r, c = sun
        glow(cr, sx, sy, r * 6, c, 0.55); glow(cr, sx, sy, r * 2, "#fff4d8", 0.8)
        col(cr, "#fff8e6"); cr.arc(sx, sy, r, 0, 6.3); cr.fill()
    if kind == "night":
        rnd = random.Random(5)
        for _ in range(140):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0 - 300, y1 * 0.7)
            a = 0.4 + 0.6 * abs(math.sin(t * rnd.uniform(1, 3) + x))
            col(cr, (1, 1, 0.92, a * rnd.uniform(0.3, 0.9))); cr.arc(x, y, rnd.uniform(0.8, 2.2), 0, 6.3); cr.fill()


def clouds(cr, y, t, c="#fff6e8", a=0.55, seed=3, x0=-600, x1=1700):
    if ANIME:
        return anime_clouds(cr, y, t, seed=seed, x0=x0, x1=x1, lit=c, a=min(1.0, a * 1.8))
    rnd = random.Random(seed)
    for k in range(6):
        cx = (rnd.uniform(x0, x1) + t * 6) % (x1 - x0) + x0; cy = y + rnd.uniform(-120, 120)
        for j in range(5):
            col(cr, (*rgb(c)[:3], a * 0.6)); ellipse(cr, cx + j * 45 - 90, cy - abs(j - 2) * -12, 70, 38); cr.fill()


def anime_clouds(cr, y, t, seed=3, x0=-600, x1=1700, lit="#ffffff", shade_c=None, a=1.0, n=5, big=1.0):
    """towering cel-shaded cumulus: lit tops, hard-edged lavender undersides"""
    rnd = random.Random(seed)
    lit_c = rgb(lit)
    sh = rgb(shade_c) if shade_c else mix(lit_c, (0.55, 0.6, 0.85, 1), 0.45)
    for k in range(n):
        cx = (rnd.uniform(x0, x1) + t * 8) % (x1 - x0) + x0; cy = y + rnd.uniform(-160, 120)
        sc = rnd.uniform(0.7, 1.3) * big
        puffs = [(rnd.uniform(-170, 170) * sc, -abs(rnd.gauss(0, 1)) * 110 * sc, rnd.uniform(55, 115) * sc) for _ in range(9)]
        puffs.sort(key=lambda q: q[1])
        cr.push_group()
        col(cr, (*sh[:3], 1))
        for (px, py, r) in puffs:
            cr.arc(cx + px, cy + py, r, 0, 6.3); cr.fill()
        cr.rectangle(cx - 230 * sc, cy, 460 * sc, 40 * sc); cr.fill()
        col(cr, (*lit_c[:3], 1))
        for (px, py, r) in puffs:
            cr.arc(cx + px - r * 0.12, cy + py - r * 0.22, r * 0.86, 0, 6.3); cr.fill()
        col(cr, (1, 1, 1, 0.6))
        for (px, py, r) in puffs[:3]:
            cr.arc(cx + px - r * 0.3, cy + py - r * 0.42, r * 0.45, 0, 6.3); cr.fill()
        cr.pop_group_to_source(); cr.paint_with_alpha(a)


def god_rays(cr, x, y, n=6, length=2600, c="#fff2c8", a=0.16, t=0.0, spread=1.1, base=-math.pi / 2 - 0.9):
    for k in range(n):
        ang = base + spread * k / max(1, n - 1) + 0.03 * math.sin(t * 0.4 + k)
        w = 0.05 + 0.03 * math.sin(k * 2.7)
        lin(cr, x, y, x + math.cos(ang) * length, y + math.sin(ang) * length, [(0, (*rgb(c)[:3], a)), (1, (*rgb(c)[:3], 0))])
        cr.move_to(x, y); cr.line_to(x + math.cos(ang - w) * length, y + math.sin(ang - w) * length)
        cr.line_to(x + math.cos(ang + w) * length, y + math.sin(ang + w) * length); cr.close_path(); cr.fill()


def rainbow(cr, x, y, r, a=0.35):
    cols = ["#ff4a4a", "#ff9a3a", "#ffe24a", "#5ad66a", "#4aa8ff", "#6a5aff", "#b05aff"]
    w = r * 0.022
    for i, c in enumerate(cols):
        col(cr, (*rgb(c)[:3], a)); cr.set_line_width(w)
        cr.arc(x, y, r - i * w, math.pi, 2 * math.pi); cr.stroke()


def puddles(cr, y0, y1, n, seed=1, sky="#8fa3b8", t=0.0, x0=-300, x1=1400):
    """flat reflective puddles with rain ripples"""
    rnd = random.Random(seed)
    for _ in range(n):
        px, py = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        w = rnd.uniform(60, 170) * (0.5 + (py - y0) / max(1, y1 - y0))
        lin(cr, 0, py - w * 0.18, 0, py + w * 0.18, [(0, shade(sky, 0.15)), (1, shade(sky, -0.1))])
        ellipse(cr, px, py, w, w * 0.2); cr.fill()
        col(cr, (1, 1, 1, 0.35)); cr.set_line_width(2)
        for j in range(2):
            ph = (t * 1.3 + rnd.random() + j * 0.5) % 1.0
            ellipse(cr, px + rnd.uniform(-0.5, 0.5) * w, py, w * 0.25 * ph, w * 0.05 * ph)
            col(cr, (1, 1, 1, 0.5 * (1 - ph))); cr.stroke()


# ------------------------------------------------------------------ vegetation
def palm(cr, x, y, h, lean=0.0, sway=0.0, trunk="#7d6650", leaf="#4f7d2c", dark=False, scale=1.0):
    cr.save(); cr.translate(x, y); cr.scale(scale, scale)
    tx, ty = lean * h, -h
    lw0, lw1 = 26, 15
    # trunk (curved, tapered, ringed)
    n = 18
    pts = [(lean * h * (i / n) ** 1.5, -h * i / n) for i in range(n + 1)]
    for i in range(n):
        w = lw0 + (lw1 - lw0) * i / n
        cr.set_line_width(w); cr.set_line_cap(cairo.LINE_CAP_BUTT)
        col(cr, shade(trunk, -0.08 if i % 2 else 0.04))
        cr.move_to(*pts[i]); cr.line_to(*pts[i + 1]); cr.stroke()
    lin(cr, -lw0, 0, lw0, 0, [(0, (0, 0, 0, 0.0)), (0.7, (0, 0, 0, 0)), (1, (0, 0, 0, 0.25))])
    tx, ty = pts[-1]
    # coconuts
    for k in range(4):
        col(cr, "#6b7a26" if not dark else shade(leaf, -0.3)); cr.arc(tx - 18 + k * 12, ty + 14 + (k % 2) * 8, 11, 0, 6.3); cr.fill()
    # fronds
    for k in range(11):
        a = -math.pi / 2 + (k - 5) * 0.33 + sway * (0.6 + 0.4 * math.sin(k))
        L = 200 + 40 * math.sin(k * 2.1)
        droop = 1.0 + 0.5 * abs(k - 5) / 5
        c = shade(leaf, -0.12 if k % 2 else 0.05)
        sp = []
        for i in range(12):
            u = i / 11
            ang = a + (math.copysign(1, math.cos(a)) * u * u * 1.4 * droop if abs(math.cos(a)) > 0.05 else 0)
            dx = math.cos(a) * L * u
            dy = math.sin(a) * L * u + 160 * droop * u * u
            sp.append((tx + dx, ty + dy))
        col(cr, c); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(4); cr.move_to(*sp[0]); [cr.line_to(*q) for q in sp[1:]]; cr.stroke()
        for i in range(1, 12):
            u = i / 11
            px, py = sp[i]; qx, qy = sp[i - 1]
            dx, dy = px - qx, py - qy; dl = math.hypot(dx, dy) or 1
            nx, ny = -dy / dl, dx / dl
            ll = 55 * math.sin(math.pi * min(1, u * 1.1)) + 8
            for sgn in (1, -1):
                cr.set_line_width(7 * (1 - u * 0.5))
                cr.move_to(px, py); cr.line_to(px + sgn * nx * ll + dx / dl * 10, py + sgn * ny * ll + 26 * u + 18); cr.stroke()
    cr.restore()


def bush(cr, x, y, r, c="#3f6b26", seed=0, flowers=None):
    rnd = random.Random(seed)
    for k in range(7):
        bx, by = x + rnd.uniform(-r, r) * 0.8, y - rnd.uniform(0.2, 0.9) * r
        rr = r * rnd.uniform(0.45, 0.7)
        rad(cr, bx - rr * 0.3, by - rr * 0.3, 0, rr * 1.3, [(0, shade(c, 0.15)), (1, shade(c, -0.2))])
        cr.arc(bx, by, rr, 0, 6.3); cr.fill()
    if flowers:
        for k in range(8):
            col(cr, flowers); cr.arc(x + rnd.uniform(-r, r) * 0.8, y - rnd.uniform(0.3, 1.1) * r, r * 0.09, 0, 6.3); cr.fill()


def banana(cr, x, y, h, c="#5c8f2e", sway=0.0, seed=0):
    rnd = random.Random(seed)
    col(cr, shade(c, -0.15)); cr.set_line_width(22); cr.move_to(x, y); cr.line_to(x, y - h); cr.stroke()
    for k in range(6):
        a = -math.pi / 2 + (k - 2.5) * 0.55 + sway * 0.5
        L = rnd.uniform(160, 220)
        ex, ey = x + math.cos(a) * L, y - h + math.sin(a) * L * 0.6 + 40
        mx, my = x + math.cos(a) * L * 0.5, y - h + math.sin(a) * L * 0.5 - 30
        lin(cr, x, y - h, ex, ey, [(0, shade(c, 0.05)), (1, shade(c, -0.15))])
        cr.move_to(x, y - h); cr.curve_to(mx - 30, my - 30, ex - 10, ey - 30, ex, ey); cr.curve_to(ex - 30, ey + 20, mx + 20, my + 40, x, y - h); cr.fill()
        col(cr, shade(c, -0.3)); cr.set_line_width(2); cr.move_to(x, y - h); cr.curve_to(mx - 5, my, ex - 15, ey - 5, ex, ey); cr.stroke()


def grass_tufts(cr, x0, x1, y, n, c="#4a7a2a", h=30, seed=1):
    rnd = random.Random(seed)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for _ in range(n):
        gx = rnd.uniform(x0, x1); gy = y + rnd.uniform(-6, 6)
        col(cr, shade(c, rnd.uniform(-0.15, 0.15)))
        for j in range(4):
            cr.set_line_width(3); cr.move_to(gx, gy); cr.curve_to(gx + (j - 1.5) * 3, gy - h * 0.6, gx + (j - 1.5) * 8, gy - h * 0.8, gx + (j - 1.5) * 10, gy - h * rnd.uniform(0.7, 1.1)); cr.stroke()


def treeline(cr, y, x0=-600, x1=1700, c="#4c6f3e", seed=4, h=160, palms=True):
    rnd = random.Random(seed)
    lin(cr, 0, y - h, 0, y + 40, [(0, shade(c, 0.1)), (1, shade(c, -0.15))])
    cr.move_to(x0, y + 60)
    x = x0
    while x < x1:
        r = rnd.uniform(45, 95)
        cr.arc(x + r, y - rnd.uniform(0.3, 1.0) * h * 0.6, r, math.pi, 0)
        x += r * 1.4
    cr.line_to(x1, y + 60); cr.close_path(); cr.fill()
    if palms:
        for k in range(9):
            palm(cr, rnd.uniform(x0, x1), y + 10, rnd.uniform(250, 380), rnd.uniform(-0.12, 0.12), 0, trunk=shade(c, -0.1), leaf=shade(c, -0.05), scale=0.6, dark=True)


# ------------------------------------------------------------------ house
def house(cr, cx, gy, s=1.0, door_open=True, aged=0.0, night=False, glow_door=False):
    """Kerala tharavadu front: tiled roof, white walls, wooden pillars, red-oxide veranda"""
    cr.save(); cr.translate(cx, gy); cr.scale(s, s)
    wall = mix("#f1e6cc", "#b8aa8c", aged); wall_d = shade(wall, -0.18)
    tile = mix("#b44a2a", "#6e3a28", aged); lat = mix("#9a4a2b", "#5e3424", aged)
    wood = "#5b351f"
    # plinth + steps
    lin(cr, 0, -110, 0, 0, [(0, lat), (1, shade(lat, -0.25))]); cr.rectangle(-560, -110, 1120, 110); cr.fill()
    col(cr, (0, 0, 0, 0.12)); cr.set_line_width(2)
    for k in range(1, 4):
        cr.move_to(-560, -110 + k * 27); cr.line_to(560, -110 + k * 27); cr.stroke()
    for k in range(3):
        col(cr, shade(lat, 0.05 - k * 0.07)); cr.rectangle(-130 - k * 18, -110 + k * 37, 260 + k * 36, 37); cr.fill()
    # veranda floor
    lin(cr, 0, -135, 0, -108, [(0, "#9a2c1d"), (1, "#6e1d12")]); cr.rectangle(-560, -135, 1120, 27); cr.fill()
    # back wall
    lin(cr, -500, 0, 500, 0, [(0, wall_d), (0.5, wall), (1, wall_d)]); cr.rectangle(-520, -560, 1040, 425); cr.fill()
    if aged > 0:
        rnd = random.Random(9)
        for _ in range(int(30 * aged)):
            rad(cr, rnd.uniform(-500, 500), rnd.uniform(-500, -150), 0, 60, [(0, (0.25, 0.22, 0.15, 0.25 * aged)), (1, (0.25, 0.22, 0.15, 0))])
            cr.arc(0, 0, 0, 0, 0); cr.rectangle(-560, -560, 1120, 430); cr.fill()
    # door
    col(cr, wood); cr.rectangle(-95, -420, 190, 290); cr.fill()
    if door_open:
        lin(cr, 0, -410, 0, -135, [(0, "#24140c"), (1, "#3c2414")]); cr.rectangle(-80, -410, 160, 275); cr.fill()
        if glow_door:
            glow(cr, 0, -260, 140, "#ffb35a", 0.5)
        col(cr, shade(wood, 0.1)); cr.rectangle(-80, -410, 26, 275); cr.fill(); cr.rectangle(54, -410, 26, 275); cr.fill()
    else:
        lin(cr, -80, 0, 80, 0, [(0, "#6e4126"), (1, "#4e2c18")]); cr.rectangle(-80, -410, 160, 275); cr.fill()
        col(cr, "#3a2112"); cr.set_line_width(4); cr.move_to(0, -410); cr.line_to(0, -135); cr.stroke()
    # windows with bars + blue-ish glass inside
    for wx in (-330, 330):
        col(cr, wood); rrect(cr, wx - 85, -420, 170, 170, 6); cr.fill()
        lin(cr, 0, -405, 0, -265, [(0, "#2c3d5a" if not night else "#ffb35a"), (1, "#1b2436" if not night else "#c46a2a")]); cr.rectangle(wx - 70, -405, 140, 140); cr.fill()
        col(cr, shade(wood, 0.15))
        for k in range(6):
            cr.rectangle(wx - 62 + k * 24, -405, 8, 140); cr.fill()
        col(cr, shade(wood, -0.2)); cr.rectangle(wx - 95, -258, 190, 12); cr.fill()
    # pillars
    for px in (-470, -200, 200, 470):
        lin(cr, px - 18, 0, px + 18, 0, [(0, shade(wood, -0.2)), (0.4, shade(wood, 0.2)), (1, shade(wood, -0.3))])
        cr.rectangle(px - 16, -585, 32, 452); cr.fill()
        col(cr, shade(lat, -0.1)); rrect(cr, px - 26, -160, 52, 28, 4); cr.fill()
        col(cr, shade(wood, 0.1)); rrect(cr, px - 24, -600, 48, 22, 4); cr.fill()
    # charupadi (low sitting wall) on sides
    for (a, b) in ((-560, -216), (216, 560)):
        col(cr, shade(lat, -0.05)); cr.rectangle(a, -230, b - a, 95); cr.fill()
        col(cr, wood); cr.rectangle(a, -240, b - a, 14); cr.fill()
    # roof beam + roof
    col(cr, shade(wood, -0.1)); cr.rectangle(-600, -615, 1200, 26); cr.fill()
    lin(cr, 0, -900, 0, -600, [(0, shade(tile, 0.08)), (1, shade(tile, -0.2))])
    cr.move_to(-680, -592); cr.line_to(-400, -880); cr.line_to(400, -880); cr.line_to(680, -592); cr.close_path(); cr.fill()
    col(cr, (0, 0, 0, 0.18)); cr.set_line_width(3)
    for k in range(1, 11):
        yy = -880 + k * 27; f = (yy + 880) / 288
        cr.move_to(-400 - 280 * f, yy); cr.line_to(400 + 280 * f, yy); cr.stroke()
    for k in range(-14, 15):
        cr.set_line_width(1.5); cr.move_to(k * 28, -880); cr.line_to(k * 48, -592); cr.stroke()
    # gable (mukhappu) with wooden lattice
    col(cr, shade(tile, -0.05)); cr.move_to(-260, -760); cr.line_to(0, -1010); cr.line_to(260, -760); cr.line_to(220, -760); cr.line_to(0, -970); cr.line_to(-220, -760); cr.close_path(); cr.fill()
    lin(cr, 0, -960, 0, -760, [(0, "#8a5a34"), (1, "#5e3a20")]); cr.move_to(-210, -762); cr.line_to(0, -965); cr.line_to(210, -762); cr.close_path(); cr.fill()
    col(cr, "#3e2412"); cr.set_line_width(5)
    for k in range(-6, 7):
        cr.move_to(k * 30, -765); cr.line_to(k * 30, -765 - (210 - abs(k * 30)) * 0.95); cr.stroke()
    col(cr, shade(tile, 0.1)); cr.set_line_width(10); cr.move_to(-400, -882); cr.line_to(400, -882); cr.stroke()
    # eave shadow on the wall
    lin(cr, 0, -590, 0, -500, [(0, (0, 0, 0, 0.35)), (1, (0, 0, 0, 0))]); cr.rectangle(-520, -590, 1040, 90); cr.fill()
    cr.restore()
    return dict(door=(cx, gy - 135 * s), chair=(cx - 330 * s, gy - 135 * s), floor=gy - 135 * s)


def chaarukasera(cr, x, y, s=1.0, rock=0.0, sling="#2e5f8a"):
    """Kerala easy chair (front three-quarter view) on gentle rockers"""
    cr.save(); cr.translate(x, y); cr.rotate(rock); cr.scale(s, s)
    wood = "#5b351f"; wl = "#7a4a2a"
    col(cr, shade(wood, -0.2)); cr.set_line_width(10); cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(-120, -10); cr.curve_to(-60, 8, 60, 8, 120, -10); cr.stroke()
    # back legs + backrest frame (leaning back)
    for sx in (-1, 1):
        limb(cr, [(sx * 95, -5), (sx * 80, -330)], 14, wood)
    # sling (striped cloth)
    cr.save()
    cr.move_to(-78, -320); cr.curve_to(-85, -200, -95, -120, -100, -90); cr.curve_to(-40, -60, 40, -60, 100, -90)
    cr.curve_to(95, -120, 85, -200, 78, -320); cr.close_path(); cr.clip()
    col(cr, "#efe6cf"); cr.paint()
    col(cr, sling)
    for k in range(-5, 6, 2):
        cr.rectangle(k * 16 - 7, -340, 14, 300); cr.fill()
    lin(cr, 0, -330, 0, -60, [(0, (0, 0, 0, 0.0)), (1, (0, 0, 0, 0.3))]); cr.paint()
    cr.restore()
    # front legs + long arm rests
    for sx in (-1, 1):
        limb(cr, [(sx * 110, -5), (sx * 112, -170)], 14, wl)
        limb(cr, [(sx * 85, -300), (sx * 125, -175), (sx * 140, -150)], 13, wl)
    col(cr, wl); cr.set_line_width(12); cr.move_to(-112, -95); cr.line_to(112, -95); cr.stroke()
    cr.restore()


def nilavilakku(cr, x, y, s=1.0, t=0.0, lit=True):
    cr.save(); cr.translate(x, y); cr.scale(s, s)
    b1, b2 = "#e6b85a", "#8a5a1a"
    lin(cr, -60, 0, 60, 0, [(0, b2), (0.4, b1), (0.6, "#fff0c0"), (1, b2)])
    cr.move_to(-55, 0); cr.curve_to(-55, -20, -20, -25, -12, -45); cr.line_to(-8, -170); cr.curve_to(-30, -175, -60, -185, -62, -200)
    cr.line_to(62, -200); cr.curve_to(60, -185, 30, -175, 8, -170); cr.line_to(12, -45); cr.curve_to(20, -25, 55, -20, 55, 0); cr.close_path(); cr.fill()
    cr.move_to(-6, -200); cr.line_to(-4, -240); cr.curve_to(-14, -250, -10, -262, 0, -270); cr.curve_to(10, -262, 14, -250, 4, -240); cr.line_to(6, -200); cr.close_path(); cr.fill()
    if lit:
        fl = 1 + 0.12 * math.sin(t * 17) + 0.06 * math.sin(t * 37)
        glow(cr, -50, -215, 170 * fl, "#ffb347", 0.55)
        for fx in (-50, 50):
            cr.save(); cr.translate(fx, -205); cr.scale(fl, fl)
            rad(cr, 0, -14, 0, 18, [(0, "#fffbe0"), (0.5, "#ffd060"), (1, (1, 0.5, 0.1, 0))])
            cr.move_to(0, -38); cr.curve_to(10, -20, 9, -4, 0, 0); cr.curve_to(-9, -4, -10, -20, 0, -38); cr.fill()
            cr.restore()
    cr.restore()


def photo_frame(cr, x, y, w, h, img=None, wood="#5b351f", sepia=0.35, garland=False):
    cr.save(); cr.translate(x, y)
    shadow(cr, 8, 10, w * 0.62, h * 0.62, 0.3)
    lin(cr, -w / 2, 0, w / 2, 0, [(0, shade(wood, -0.2)), (0.5, shade(wood, 0.15)), (1, shade(wood, -0.25))])
    rrect(cr, -w / 2 - 22, -h / 2 - 22, w + 44, h + 44, 6); cr.fill()
    if img is not None:
        cr.save(); cr.rectangle(-w / 2, -h / 2, w, h); cr.clip()
        cr.translate(-w / 2, -h / 2); cr.scale(w / img.get_width(), h / img.get_height())
        cr.set_source_surface(img, 0, 0); cr.paint()
        cr.restore()
        col(cr, (0.75, 0.55, 0.3, sepia)); cr.rectangle(-w / 2, -h / 2, w, h); cr.fill()
        rad(cr, 0, 0, w * 0.2, w * 0.8, [(0, (0, 0, 0, 0)), (1, (0.2, 0.1, 0.0, 0.35))]); cr.rectangle(-w / 2, -h / 2, w, h); cr.fill()
    if garland:
        for k in range(17):
            a = math.pi * k / 16
            gx = -w / 2 - 10 + (w + 20) * k / 16; gy = -h / 2 - 22 + 40 * math.sin(a) * 0 + (18 if k % 2 else 0) * 0
            col(cr, "#e8901a" if k % 3 else "#f2c230"); cr.arc(gx, -h / 2 - 22 + 30 * math.sin(a), 13, 0, 6.3); cr.fill()
    cr.restore()


def toys(cr, x, y, s=1.0):
    cr.save(); cr.translate(x, y); cr.scale(s, s)
    shadow(cr, -150, 5, 70, 14); shadow(cr, 40, 5, 110, 16); shadow(cr, 230, 5, 60, 12)
    # spinning top lying on its side
    cr.save(); cr.translate(-160, -30); cr.rotate(-1.2)
    lin(cr, -40, 0, 40, 0, [(0, "#c8461d"), (0.5, "#f2b030"), (1, "#c8461d")])
    cr.move_to(-40, 0); cr.curve_to(-40, -45, 40, -45, 40, 0); cr.line_to(0, 60); cr.close_path(); cr.fill()
    col(cr, "#3a2a1a"); cr.set_line_width(4); cr.move_to(0, 60); cr.line_to(0, 75); cr.stroke(); cr.restore()
    # toy car
    col(cr, "#c8201e"); rrect(cr, -50, -60, 190, 50, 14); cr.fill(); rrect(cr, -10, -95, 100, 45, 14); cr.fill()
    col(cr, "#bfe4f0"); rrect(cr, 0, -88, 38, 30, 6); cr.fill(); rrect(cr, 46, -88, 36, 30, 6); cr.fill()
    for wx in (-10, 100):
        col(cr, "#1a1512"); cr.arc(wx, -10, 22, 0, 6.3); cr.fill(); col(cr, "#999"); cr.arc(wx, -10, 8, 0, 6.3); cr.fill()
    col(cr, (1, 1, 1, 0.35)); rrect(cr, -40, -56, 120, 8, 4); cr.fill()
    # ball
    rad(cr, 215, -75, 5, 60, [(0, "#ffe680"), (1, "#c79a1a")]); cr.arc(230, -55, 55, 0, 6.3); cr.fill()
    col(cr, "#2a6fc9"); cr.set_line_width(14); cr.arc(230, -55, 48, 2.2, 4.0); cr.stroke(); cr.arc(230, -55, 48, 5.3, 7.1); cr.stroke()
    cr.restore()


def petti_kada(cr, x, y, s=1.0):
    cr.save(); cr.translate(x, y); cr.scale(s, s)
    wood, wl = "#5b351f", "#8a5a34"
    for px in (-230, 230):
        col(cr, wood); cr.rectangle(px - 10, -560, 20, 560); cr.fill()
    lin(cr, 0, -340, 0, 0, [(0, wl), (1, shade(wl, -0.3))]); cr.rectangle(-220, -330, 440, 330); cr.fill()
    col(cr, shade(wl, -0.25)); cr.set_line_width(3)
    for k in range(1, 8):
        cr.move_to(-220 + k * 55, -330); cr.line_to(-220 + k * 55, 0); cr.stroke()
    col(cr, "#6f7f86"); cr.move_to(-290, -540); cr.line_to(290, -540); cr.line_to(260, -600); cr.line_to(-260, -600); cr.close_path(); cr.fill()
    col(cr, shade(wood, -0.1)); cr.rectangle(-240, -345, 480, 22); cr.fill()
    lin(cr, 0, -540, 0, -350, [(0, "#2a1c12"), (1, "#3e2a1a")]); cr.rectangle(-220, -540, 440, 195); cr.fill()
    cols = ["#e8452b", "#f2c230", "#3aa65a", "#ec7fb0", "#7a4a2a"]
    for k in range(5):
        jx = -180 + k * 90
        col(cr, cols[k]); rrect(cr, jx - 30, -425, 60, 70, 10); cr.fill()
        col(cr, (0.85, 0.95, 1, 0.35)); rrect(cr, jx - 34, -440, 68, 92, 12); cr.fill()
        col(cr, (1, 1, 1, 0.6)); rrect(cr, jx - 24, -432, 10, 70, 5); cr.fill()
        col(cr, "#b22222"); rrect(cr, jx - 32, -450, 64, 14, 4); cr.fill()
    for k in range(12):
        col(cr, "#e6c13a" if k % 2 else "#d8b02a"); ellipse(cr, 170 + (k % 4) * 14, -520 + (k // 4) * 22, 9, 22, 0.3); cr.fill()
    pk = ["#e63", "#36c", "#fc3", "#3a6", "#c3c", "#f63"]
    for k in range(6):
        col(cr, pk[k]); cr.rectangle(-200 + k * 40, -535, 30, 45); cr.fill()
    cr.restore()


# ------------------------------------------------------------------ rooms
def kitchen(cr, t=0.0):
    lin(cr, 0, 0, 0, 1300, [(0, "#b99a72"), (1, "#e0c79c")]); cr.rectangle(-400, -400, 1900, 1700); cr.fill()
    # window with sunlight
    col(cr, "#4e2e18"); rrect(cr, 90, 280, 300, 330, 8); cr.fill()
    lin(cr, 0, 300, 0, 590, [(0, "#fff2c8"), (1, "#f6c878")]); cr.rectangle(110, 300, 260, 290); cr.fill()
    palm(cr, 260, 640, 330, 0.08, 0.05 * math.sin(t), leaf="#6c9a3a", scale=0.7)
    col(cr, "#4e2e18")
    for k in range(6):
        cr.rectangle(120 + k * 46, 300, 10, 290); cr.fill()
    # light shafts
    for k in range(3):
        lin(cr, 250, 450, 700, 1350, [(0, (1, 0.9, 0.6, 0.22)), (1, (1, 0.9, 0.6, 0))])
        cr.move_to(110 + k * 80, 300); cr.line_to(190 + k * 80, 300); cr.line_to(800 + k * 110, 1400); cr.line_to(620 + k * 110, 1400); cr.close_path(); cr.fill()
    # shelves
    col(cr, "#5b351f"); cr.rectangle(560, 330, 420, 18); cr.fill(); cr.rectangle(560, 520, 420, 18); cr.fill()
    for k in range(5):
        lin(cr, 590 + k * 80, 0, 630 + k * 80, 0, [(0, "#8d9396"), (0.5, "#f2f4f5"), (1, "#8d9396")]); rrect(cr, 590 + k * 80, 270, 42, 60, 5); cr.fill()
    for k in range(4):
        col(cr, ["#9a5a2a", "#c7a33a", "#7a3a1a", "#d9c07a"][k]); rrect(cr, 590 + k * 95, 440, 70, 80, 14); cr.fill()
    # hearth (adupp): clay platform, pots on top, fire openings in front
    lin(cr, 0, 760, 0, 1060, [(0, "#9a5a36"), (1, "#6a3820")]); rrect(cr, 520, 760, 620, 300, 16); cr.fill()
    col(cr, "#b0714a"); rrect(cr, 510, 740, 640, 34, 10); cr.fill()
    for k, fx in enumerate((660, 920)):
        col(cr, "#1e0f08"); cr.move_to(fx - 70, 1050); cr.line_to(fx - 70, 960); cr.curve_to(fx - 70, 900, fx + 70, 900, fx + 70, 960); cr.line_to(fx + 70, 1050); cr.close_path(); cr.fill()
        col(cr, "#1b1512" if k == 0 else "#c9932e"); cr.move_to(fx - 100, 742); cr.curve_to(fx - 120, 600, fx + 120, 600, fx + 100, 742); cr.close_path(); cr.fill()
        col(cr, shade("#1b1512" if k == 0 else "#c9932e", -0.2)); ellipse(cr, fx, 642, 62, 14); cr.fill()
        col(cr, (1, 1, 1, 0.12)); ellipse(cr, fx - 50, 690, 14, 30, 0.3); cr.fill()
    # hanging banana bunch
    col(cr, "#5b351f"); cr.set_line_width(4); cr.move_to(470, 0); cr.line_to(470, 150); cr.stroke()
    for k in range(10):
        col(cr, "#e6c13a" if k % 2 else "#d0a82a"); ellipse(cr, 450 + (k % 3) * 20, 170 + (k // 3) * 28, 12, 30, 0.3); cr.fill()
    # floor
    lin(cr, 0, 1050, 0, 1950, [(0, "#8a2a1a"), (1, "#4e140c")]); cr.rectangle(-400, 1050, 1900, 1000); cr.fill()
    lin(cr, 0, 1050, 0, 1300, [(0, (1, 0.8, 0.6, 0.2)), (1, (1, 0.8, 0.6, 0))]); cr.rectangle(-400, 1050, 1900, 250); cr.fill()


def bedroom(cr, night=True, t=0.0, aged=0.0):
    wall = "#d8c3a0" if not night else "#4a3a32"
    lin(cr, 0, 0, 0, 1300, [(0, shade(wall, -0.25)), (1, wall)]); cr.rectangle(-400, -400, 1900, 1700); cr.fill()
    # window
    col(cr, "#4e2e18"); rrect(cr, 640, 250, 300, 360, 8); cr.fill()
    if night:
        lin(cr, 0, 270, 0, 590, [(0, "#0c1b38"), (1, "#24406a")]); cr.rectangle(660, 270, 260, 320); cr.fill()
        col(cr, "#fff6d8"); cr.arc(840, 340, 32, 0, 6.3); cr.fill(); glow(cr, 840, 340, 120, "#bcd4ff", 0.35)
        palm(cr, 720, 650, 300, 0.1, 0.05 * math.sin(t * 0.8), trunk="#101a28", leaf="#13233a", scale=0.7, dark=True)
    else:
        lin(cr, 0, 270, 0, 590, [(0, "#ffe6b0"), (1, "#f2a85a")]); cr.rectangle(660, 270, 260, 320); cr.fill()
        palm(cr, 720, 650, 300, 0.1, 0.05 * math.sin(t * 0.8), leaf="#6c8a3a", scale=0.7)
        for k in range(3):
            lin(cr, 700, 420, 200, 1400, [(0, (1, 0.85, 0.55, 0.25)), (1, (1, 0.85, 0.55, 0))])
            cr.move_to(660 + k * 90, 270); cr.line_to(740 + k * 90, 270); cr.line_to(260 + k * 120, 1400); cr.line_to(60 + k * 120, 1400); cr.close_path(); cr.fill()
    col(cr, "#4e2e18")
    for k in range(6):
        cr.rectangle(670 + k * 46, 270, 10, 320); cr.fill()
    # wall clock
    col(cr, "#5b351f"); cr.arc(220, 260, 70, 0, 6.3); cr.fill(); col(cr, "#f4ecd8"); cr.arc(220, 260, 56, 0, 6.3); cr.fill()
    col(cr, "#2a1a10"); cr.set_line_width(5); cr.move_to(220, 260); cr.line_to(220 + 35 * math.sin(t * 0.1), 260 - 35 * math.cos(t * 0.1)); cr.stroke()
    cr.set_line_width(3); cr.move_to(220, 260); cr.line_to(220 + 45 * math.sin(t * 1.0), 260 - 45 * math.cos(t * 1.0)); cr.stroke()
    # floor
    lin(cr, 0, 1050, 0, 1950, [(0, "#7a2416" if not night else "#3a120c"), (1, "#3a0e08" if not night else "#1a0604")]); cr.rectangle(-400, 1050, 1900, 1000); cr.fill()
    if night:
        col(cr, (0.02, 0.03, 0.08, 0.45)); cr.rectangle(-400, -400, 1900, 2400); cr.fill()
    if aged:
        col(cr, (0.35, 0.3, 0.25, 0.12 * aged)); cr.rectangle(-400, -400, 1900, 2400); cr.fill()


def cot(cr, x, y, w=760, night=True, made=False):
    """wooden cot (kattil) seen from its foot end"""
    wood = "#5b351f"
    col(cr, shade(wood, -0.1)); rrect(cr, x - w / 2 - 20, y - 560, w + 40, 300, 16); cr.fill()   # headboard
    col(cr, shade(wood, 0.1)); cr.set_line_width(5)
    for k in range(1, 6):
        cr.move_to(x - w / 2 + k * w / 6, y - 545); cr.line_to(x - w / 2 + k * w / 6, y - 280); cr.stroke()
    lin(cr, 0, y - 300, 0, y, [(0, "#efe6d2"), (1, "#c9bea6")]); rrect(cr, x - w / 2, y - 330, w, 280, 30); cr.fill()   # mattress top (foreshortened)
    lin(cr, 0, y - 60, 0, y + 60, [(0, shade(wood, 0.05)), (1, shade(wood, -0.25))]); cr.rectangle(x - w / 2 - 20, y - 60, w + 40, 70); cr.fill()
    for sx in (-1, 1):
        col(cr, shade(wood, -0.2)); cr.rectangle(x + sx * (w / 2 + 5) - 14, y, 28, 160); cr.fill()
    # pillow
    rad(cr, x - 40, y - 300, 10, 200, [(0, "#ffffff"), (1, "#d8d0c0")]); ellipse(cr, x, y - 290, 190, 55); cr.fill()


def kitchen_fire(cr, t):
    for k, fx in enumerate((660, 920)):
        fl = 1 + 0.15 * math.sin(t * 9 + k) + 0.08 * math.sin(t * 23 + k)
        glow(cr, fx, 1000, 170 * fl, "#ff7a20", 0.4)
        for j in range(3):
            cr.save(); cr.translate(fx - 35 + j * 35, 1045); cr.scale(fl * (0.8 + 0.2 * j % 2), fl)
            rad(cr, 0, -12, 0, 30, [(0, "#fff2b0"), (0.5, "#ffa030"), (1, (1, 0.4, 0.1, 0))])
            cr.move_to(0, -50); cr.curve_to(16, -25, 14, -5, 0, 0); cr.curve_to(-14, -5, -16, -25, 0, -50); cr.fill(); cr.restore()
