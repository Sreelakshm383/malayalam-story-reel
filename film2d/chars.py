"""2D illustrated characters (front / three-quarter view), soft-shaded cartoon style,
or (REEL_STYLE=anime) cel-shaded anime style with big glossy eyes and ink outlines.

Every character is drawn by draw_person() from a fixed SPEC, so face, hair,
clothes, proportions and colours never change between scenes.
Units: R = head radius in px. (x, y) = point between the feet on the ground.
"""
import math
import cairo
from draw import rgb, shade, mix, col, lin, rad, ellipse, rrect, smooth, limb, shadow, glow, cel, ANIME

SPEC = {
    "child": dict(R=1.0, torso=1.55, legs=1.75, arm=(0.85, 0.8), sw=0.78, ww=0.72, limb=0.24, neck=0.12,
                  skin="#b67a4f", hair="#1c1410", style="kid", eye=1.3, top="#f4b82e", trim="#e2622a",
                  bottom="#1f8c87", clothes="kid", iris="#3d2414", headry=1.0),
    "grandma": dict(R=1.0, torso=2.35, legs=3.0, arm=(1.25, 1.15), sw=1.18, ww=1.18, limb=0.26, neck=0.2,
                    skin="#a46c47", hair="#cfcac3", style="bun", eye=1.08, top="#8a2131", trim="#d6a53a",
                    bottom="#f4eddc", clothes="saree", iris="#2e1c10", headry=1.04, old=True, lashes=True),
    "grandpa": dict(R=1.0, torso=2.5, legs=3.3, arm=(1.32, 1.2), sw=1.2, ww=1.15, limb=0.26, neck=0.22,
                    skin="#956243", hair="#dedad3", style="bald", eye=1.02, top="#f1e9d6", trim="#d6a53a",
                    bottom="#f8f5ee", clothes="mundu", iris="#2e1c10", headry=1.07, old=True),
    "adult": dict(R=1.0, torso=2.5, legs=3.4, arm=(1.32, 1.22), sw=1.15, ww=0.98, limb=0.25, neck=0.24,
                  skin="#ae7650", hair="#1c1410", style="adult", eye=1.05, top="#eaa92c", trim="#e2622a",
                  bottom="#2f5d63", clothes="adult", iris="#3d2414", headry=1.08),
    # --- "Achante Kuda" (Father's Umbrella) cast
    "girl": dict(R=1.0, torso=1.5, legs=1.8, arm=(0.85, 0.8), sw=0.74, ww=0.68, limb=0.22, neck=0.13,
                 skin="#c48a5c", hair="#1b1216", style="ponytail", eye=1.32, top="#f7f5ef", trim="#27407e",
                 bottom="#27407e", clothes="skirt", iris="#5a2f1c", iris2="#c9853a", headry=1.0, lashes=True),
    "father": dict(R=1.0, torso=2.5, legs=3.4, arm=(1.32, 1.22), sw=1.18, ww=1.05, limb=0.26, neck=0.24,
                   skin="#9e6a45", hair="#18110d", style="adult", eye=1.0, top="#7c9cc0", trim="#56779c",
                   bottom="#f5f0e2", clothes="mundu", iris="#33200f", iris2="#8a5a2a", headry=1.08, towel=False),
    "father_old": dict(R=1.0, torso=2.45, legs=3.3, arm=(1.3, 1.2), sw=1.15, ww=1.08, limb=0.25, neck=0.22,
                       skin="#94613f", hair="#d9d5ce", style="adult", eye=0.98, top="#e9e1cf", trim="#b9a888",
                       bottom="#f5f0e2", clothes="mundu", iris="#33200f", iris2="#8a5a2a", headry=1.08, old=True,
                       mous="#cfcac2", towel=True),
    "woman": dict(R=1.0, torso=2.4, legs=3.4, arm=(1.28, 1.18), sw=0.98, ww=0.86, limb=0.22, neck=0.24,
                  skin="#c48a5c", hair="#1b1216", style="long", eye=1.16, top="#b8325a", trim="#e0b04a",
                  bottom="#f1e4cc", clothes="kurta", iris="#5a2f1c", iris2="#c9853a", headry=1.04, lashes=True),
}
PANTS = ("kid", "adult", "skirt", "kurta")

DEFAULT = dict(turn=0.0, tilt=0.0, mouth=0.0, smile=0.7, blink=0.0, gaze=(0.0, 0.0), brows=0.0, lean=0.0,
               armL=(8, 10), armR=(8, 10), legs="stand", happy_eyes=False, sleepy=0.0, body_turn=0.0,
               hold=None, bob=0.0, squash=0.0, back=False, alpha=1.0, tears=0.0, hair_sway=0.0, wet=0.0)


def arm_points(sx, shx, shy, a1, a2, L1, L2):
    """a1: upper arm angle from straight-down, +outward (deg); a2: elbow bend, + folds forearm up/inward"""
    t1 = math.radians(a1)
    ex, ey = shx + sx * math.sin(t1) * L1, shy + math.cos(t1) * L1
    t2 = t1 - math.radians(a2)
    hx, hy = ex + sx * math.sin(t2) * L2, ey + math.cos(t2) * L2
    return (shx, shy), (ex, ey), (hx, hy)


def ik(sx, shx, shy, tx, ty, L1, L2, bend_up=True):
    """2-bone IK in screen space -> (a1, a2) in this module's convention"""
    dx, dy = (tx - shx) * sx, ty - shy
    D = max(abs(L1 - L2) + 1e-3, min(L1 + L2 - 1e-3, math.hypot(dx, dy)))
    base = math.degrees(math.atan2(dx, dy))   # angle from down, + outward
    c1 = (L1 * L1 + D * D - L2 * L2) / (2 * L1 * D)
    off = math.degrees(math.acos(max(-1, min(1, c1))))
    ce = (L1 * L1 + L2 * L2 - D * D) / (2 * L1 * L2)
    bend = 180 - math.degrees(math.acos(max(-1, min(1, ce))))
    return (base + off, bend) if bend_up else (base - off, -bend)


class Rig:
    """computed joint positions so shots can attach props / aim hands"""
    pass


def draw_person(cr, key, x, y, R, **pose):
    p = dict(DEFAULT); p.update(pose)
    if p["alpha"] < 0.999:
        cr.push_group()
        rig = draw_person(cr, key, x, y, R, **dict(pose, alpha=1.0))
        cr.pop_group_to_source(); cr.paint_with_alpha(max(0.0, p["alpha"]))
        return rig
    if ANIME:
        s = SPEC[key]
        top = (s["legs"] + s["torso"] + s["neck"] + s["headry"] * 2 + 0.6) * R
        return cel(cr, (x - 4.2 * R, y - top, x + 4.2 * R, y + 0.6 * R), lambda c2: _draw_person(c2, key, x, y, R, p), R)
    return _draw_person(cr, key, x, y, R, p)


def draw_head_at(cr, key, x, y, R, **pose):
    """just a head (e.g. on a pillow), centred at (x, y)"""
    p = dict(DEFAULT); p.update(pose)
    def f(c):
        c.save(); c.translate(x, y); c.scale(R, R); c.rotate(p["tilt"])
        draw_head(c, key, SPEC[key], p); c.restore()
    if ANIME:
        return cel(cr, (x - 1.8 * R, y - 1.8 * R, x + 1.8 * R, y + 1.8 * R), f, R)
    return f(cr)


def _draw_person(cr, key, x, y, R, p):
    s = SPEC[key]
    rig = Rig(); rig.R = R
    cr.save()
    cr.translate(x, y); cr.scale(R, R)
    skin = s["skin"]; sk_d = shade(skin, -0.22); sk_l = shade(skin, 0.12)
    legs = p["legs"]
    sitting = isinstance(legs, tuple) and legs[0] == "sit"
    walk = isinstance(legs, tuple) and legs[0] == "walk"
    seat = legs[1] if sitting else 0.0
    L = s["legs"]
    hipY = -(L if not sitting else seat) - p["bob"]
    shY = hipY - s["torso"]
    neckY = shY - s["neck"]
    headY = neckY - s["headry"] * 0.95
    lean = p["lean"]
    bt = p["body_turn"]
    sw, ww = s["sw"], s["ww"]
    lw = s["limb"]

    # ---------------- ground shadow
    shadow(cr, 0, 0.02, 1.25 if key != "child" else 0.95, 0.2, 0.32)

    # ---------------- legs / lower body
    def foot(fx, fy, c):
        col(cr, c); ellipse(cr, fx, fy - 0.08, 0.24, 0.12); cr.fill()

    if s["clothes"] in PANTS:
        lc = skin if s["clothes"] in ("kid", "skirt") else s["bottom"]
        for i, sx in enumerate((-1, 1)):
            hx = sx * ww * 0.42
            if sitting:
                kx, ky = sx * ww * 0.5, hipY + 0.15
                fx, fy = sx * ww * 0.55, 0.0
                limb(cr, [(hx, hipY), (kx, ky)], lw * 1.35, shade(lc, -0.05))
                limb(cr, [(kx, ky), (fx, fy - 0.12)], lw * 1.2, lc)
                foot(fx, fy, sk_d if key == "child" else ("#1c1a22" if s["clothes"] == "skirt" else "#4a2e1d"))
            else:
                lift = 0.0; sw_ = 0.0
                if walk:
                    ph = legs[1] + (0 if sx < 0 else math.pi)
                    lift = max(0, math.sin(ph)) * (0.35 if len(legs) < 3 else legs[2])
                    sw_ = 0.05 * math.cos(ph)
                fx, fy = sx * ww * 0.38 + sw_, -lift
                kx, ky = (hx + fx) / 2 + sx * 0.03, (hipY + fy) / 2 - lift * 0.3
                limb(cr, [(hx, hipY), (kx, ky), (fx, fy - 0.12)], lw * 1.35, lc, lw * 1.1)
                if key == "child":
                    foot(fx, fy, sk_d)
                elif s["clothes"] == "skirt":   # white socks + black school shoes
                    limb(cr, [(fx, fy - 0.45), (fx, fy - 0.14)], lw * 1.2, "#f4f2ec")
                    col(cr, "#1c1a22"); ellipse(cr, fx + sx * 0.03, fy - 0.08, 0.26, 0.13); cr.fill()
                else:
                    col(cr, "#4a2e1d"); ellipse(cr, fx, fy - 0.05, 0.27, 0.09); cr.fill()
                    foot(fx, fy - 0.02, sk_d)
        if s["clothes"] == "kid":   # shorts
            lin(cr, 0, hipY - 0.3, 0, hipY + 0.45, [(0, s["bottom"]), (1, shade(s["bottom"], -0.25))])
            cr.move_to(-ww * 0.98, hipY - 0.35); cr.line_to(ww * 0.98, hipY - 0.35)
            cr.line_to(ww * 1.02, hipY + 0.42); cr.line_to(0.06, hipY + 0.4); cr.line_to(0, hipY + 0.2)
            cr.line_to(-0.06, hipY + 0.4); cr.line_to(-ww * 1.02, hipY + 0.42); cr.close_path(); cr.fill()
        if s["clothes"] == "skirt":   # pleated school skirt
            b = s["bottom"]; sk_top, sk_bot = hipY - 0.4, hipY + (0.55 if sitting else 0.85)
            lin(cr, -ww * 1.4, 0, ww * 1.4, 0, [(0, shade(b, -0.2)), (0.4, b), (1, shade(b, -0.25))])
            cr.move_to(-ww * 1.0, sk_top); cr.line_to(ww * 1.0, sk_top); cr.line_to(ww * 1.5, sk_bot)
            cr.curve_to(ww * 0.5, sk_bot + 0.08, -ww * 0.5, sk_bot + 0.08, -ww * 1.5, sk_bot); cr.close_path(); cr.fill()
            col(cr, shade(b, -0.3)); cr.set_line_width(0.035)
            for k in range(-2, 3):
                cr.move_to(k * ww * 0.3, sk_top + 0.08); cr.line_to(k * ww * 0.52, sk_bot); cr.stroke()
    else:
        # mundu / saree: long cloth to the ankles with gold kasavu border
        cloth = s["bottom"]
        if sitting:
            top, bot = hipY - 0.25, -0.05
            wtop, wbot = ww * 1.05, ww * 1.45
        else:
            top, bot = hipY - 0.25, -0.18
            wtop, wbot = ww * 1.0, ww * (1.22 if s["clothes"] == "saree" else 1.1)
        # feet peeking out
        for sx in (-1, 1):
            fx = sx * 0.3 + (0.04 * math.sin(legs[1] + (sx > 0) * math.pi) if walk else 0)
            fl = max(0, math.sin(legs[1] + (0 if sx < 0 else math.pi))) * 0.12 if walk else 0
            col(cr, "#4a2e1d"); ellipse(cr, fx, -0.05 - fl, 0.27, 0.09); cr.fill()
            col(cr, sk_d); ellipse(cr, fx, -0.1 - fl, 0.22, 0.1); cr.fill()
        sway = 0.04 * math.sin(legs[1]) if walk else 0
        lin(cr, -wbot, 0, wbot, 0, [(0, shade(cloth, -0.18)), (0.35, cloth), (0.7, shade(cloth, 0.05)), (1, shade(cloth, -0.22))])
        cr.move_to(-wtop, top); cr.line_to(wtop, top)
        cr.curve_to(wtop * 1.05, (top + bot) / 2, wbot + sway, bot - 0.4, wbot + sway, bot)
        cr.curve_to(wbot * 0.5, bot + 0.06, -wbot * 0.5, bot + 0.06, -wbot + sway, bot)
        cr.curve_to(-wbot + sway, bot - 0.4, -wtop * 1.05, (top + bot) / 2, -wtop, top)
        cr.close_path(); cr.fill()
        # kasavu border
        col(cr, s["trim"]); cr.set_line_width(0.09)
        cr.move_to(-wbot + sway + 0.03, bot - 0.16); cr.curve_to(-wbot * 0.5, bot - 0.1, wbot * 0.5, bot - 0.1, wbot + sway - 0.03, bot - 0.16); cr.stroke()
        col(cr, shade(cloth, -0.15)); cr.set_line_width(0.035)
        if s["clothes"] == "saree":
            for k in range(4):   # pleats
                px = -0.12 + k * 0.09
                cr.move_to(px, top + 0.5); cr.curve_to(px - 0.02, (top + bot) / 2, px + 0.02, bot - 0.5, px + 0.03 * (k - 1.5), bot - 0.05); cr.stroke()
        else:   # mundu front fold
            cr.move_to(0.18, top + 0.1); cr.curve_to(0.22, (top + bot) / 2, 0.15, bot - 0.4, 0.25, bot - 0.02); cr.stroke()
            col(cr, s["trim"]); cr.set_line_width(0.06)
            cr.move_to(0.25, bot - 0.08); cr.line_to(0.22, bot - 0.9); cr.stroke()

    # ---------------- torso
    cr.save(); cr.translate(lean * 0.5, 0)
    top_c = s["top"]
    tl, tr_ = -sw, sw
    hemY = hipY + {"kid": 0.55, "adult": 0.15, "skirt": -0.3, "kurta": 1.25}.get(s["clothes"], -0.1)
    if s["clothes"] == "saree":
        hemY = hipY - s["torso"] * 0.55
    lin(cr, -sw, 0, sw, 0, [(0, shade(top_c, -0.22)), (0.3 + 0.15 * bt, top_c), (0.65 + 0.15 * bt, shade(top_c, 0.08)), (1, shade(top_c, -0.25))])
    cr.move_to(-sw * 0.55, shY - 0.08)
    cr.curve_to(-sw * 0.95, shY - 0.05, -sw * 1.02, shY + 0.15, -sw * 1.0, shY + 0.4)
    fl = 1.3 if s["clothes"] == "kurta" else 1.0
    cr.curve_to(-ww * 1.0, (shY + hemY) / 2, -ww * 1.02 * fl, hemY - 0.3, -ww * 1.02 * fl, hemY)
    cr.curve_to(-ww * 0.4, hemY + 0.06, ww * 0.4, hemY + 0.06, ww * 1.02 * fl, hemY)
    cr.curve_to(ww * 1.02 * fl, hemY - 0.3, ww * 1.0, (shY + hemY) / 2, sw * 1.0, shY + 0.4)
    cr.curve_to(sw * 1.02, shY + 0.15, sw * 0.95, shY - 0.05, sw * 0.55, shY - 0.08)
    cr.close_path(); cr.fill()
    if s["clothes"] == "saree":
        # saree wrap over the waist + pallu across the chest to the left shoulder
        cloth = s["bottom"]
        lin(cr, -sw, 0, sw, 0, [(0, shade(cloth, -0.18)), (0.5, cloth), (1, shade(cloth, -0.2))])
        cr.move_to(-ww * 1.02, hemY - 0.05); cr.line_to(ww * 1.03, hemY - 0.05); cr.line_to(ww * 1.02, hipY - 0.2); cr.line_to(-ww * 1.0, hipY - 0.2); cr.close_path(); cr.fill()
        lin(cr, 0, shY, 0, hipY, [(0, shade(cloth, 0.03)), (1, shade(cloth, -0.12))])
        cr.move_to(sw * 0.35, shY - 0.1); cr.line_to(sw * 1.02, shY + 0.1); cr.line_to(sw * 1.0, shY + 0.75)
        cr.curve_to(0.3, hipY - 0.6, -0.3, hipY - 0.2, -ww * 1.03, hipY - 0.15)
        cr.line_to(-ww * 1.02, hipY - 0.75); cr.curve_to(-0.4, hipY - 0.9, 0.0, shY + 0.6, sw * 0.35, shY - 0.1)
        cr.close_path(); cr.fill()
        col(cr, s["trim"]); cr.set_line_width(0.08)
        cr.move_to(sw * 0.33, shY - 0.05); cr.curve_to(0.0, shY + 0.65, -0.4, hipY - 0.85, -ww * 1.02, hipY - 0.72); cr.stroke()
        col(cr, shade(cloth, -0.14)); cr.set_line_width(0.03)
        for k in range(3):
            cr.move_to(sw * 0.5 + k * 0.12, shY + 0.05); cr.curve_to(0.3 + k * 0.1, shY + 0.9, -0.1 + k * 0.1, hipY - 0.6, -0.5 + k * 0.12, hipY - 0.35); cr.stroke()
    if s["clothes"] == "kurta":   # gold border along the kurta hem
        col(cr, s["trim"]); cr.set_line_width(0.08)
        cr.move_to(-ww * 1.3, hemY - 0.08); cr.curve_to(-ww * 0.4, hemY - 0.02, ww * 0.4, hemY - 0.02, ww * 1.3, hemY - 0.08); cr.stroke()
    if s["clothes"] in PANTS and not p["back"]:
        col(cr, s["trim"])
        cr.move_to(-0.32, shY - 0.06); cr.curve_to(-0.2, shY + 0.2, 0.2, shY + 0.2, 0.32, shY - 0.06)
        cr.line_to(0.2, shY - 0.1); cr.curve_to(0.1, shY + 0.06, -0.1, shY + 0.06, -0.2, shY - 0.1); cr.close_path(); cr.fill()
        rrect(cr, -0.055, shY + 0.1, 0.11, 0.55 if s["clothes"] in ("kid", "skirt") else 0.8, 0.04); cr.fill()
        if s["clothes"] == "kid":
            col(cr, shade(s["trim"], -0.05)); cr.set_line_width(0.06)
            cr.move_to(-ww * 1.0, hemY - 0.04); cr.curve_to(-ww * 0.4, hemY + 0.02, ww * 0.4, hemY + 0.02, ww * 1.0, hemY - 0.04); cr.stroke()
    if s["clothes"] == "mundu":
        col(cr, shade(top_c, -0.12))
        cr.move_to(-0.3, shY - 0.06); cr.line_to(0, shY + 0.32); cr.line_to(0.3, shY - 0.06); cr.line_to(0.2, shY - 0.1); cr.line_to(0, shY + 0.18); cr.line_to(-0.2, shY - 0.1); cr.close_path(); cr.fill()
        for k in range(4):
            col(cr, "#d9d0bc"); cr.arc(0, shY + 0.45 + k * 0.42, 0.045, 0, 2 * math.pi); cr.fill()
        col(cr, shade(top_c, -0.1)); cr.set_line_width(0.025)
        rrect(cr, -0.75, shY + 0.45, 0.38, 0.4, 0.04); cr.stroke()
    if s["clothes"] == "mundu" and s.get("towel", True):
        # towel (thorthu) over the shoulder
        lin(cr, sw * 0.4, 0, sw * 1.1, 0, [(0, "#f6f1e4"), (1, "#d9cfb8")])
        cr.move_to(sw * 0.45, shY - 0.08); cr.curve_to(sw * 0.9, shY - 0.12, sw * 1.05, shY + 0.1, sw * 1.0, shY + 1.4)
        cr.line_to(sw * 0.72, shY + 1.4); cr.curve_to(sw * 0.75, shY + 0.4, sw * 0.6, shY + 0.1, sw * 0.4, shY + 0.05); cr.close_path(); cr.fill()
        col(cr, "#c4553a"); cr.set_line_width(0.05); cr.move_to(sw * 0.72, shY + 1.3); cr.line_to(sw * 1.0, shY + 1.3); cr.stroke()
    cr.restore()

    # ---------------- arms
    L1, L2 = s["arm"]
    rig.shoulder = {}
    rig.hand = {}
    def draw_arm(sx, a):
        shx, shy = sx * (sw * 0.9) + lean * 0.5, shY + 0.22
        if isinstance(a, dict):   # IK target in screen px, relative to (x, y)
            tx, ty = a["target"]
            a = ik(sx, shx, shy, tx / R, ty / R, L1, L2, a.get("up", True))
        p0, p1, p2 = arm_points(sx, shx, shy, a[0], a[1], L1, L2)
        sleeve = {"kid": 0.45, "saree": 0.4, "mundu": 0.55, "adult": 0.5, "skirt": 0.4, "kurta": 0.8}[s["clothes"]]
        limb(cr, [p0, p1, p2], lw * 1.25, sk_d if sx > 0 else skin, lw * 1.05)
        sx1 = p0[0] + (p1[0] - p0[0]) * sleeve; sy1 = p0[1] + (p1[1] - p0[1]) * sleeve
        limb(cr, [p0, (sx1, sy1)], lw * 1.75, shade(top_c, -0.08 if sx > 0 else 0.0))
        if s["clothes"] in ("kid", "saree", "skirt", "kurta"):
            col(cr, s["trim"]); cr.set_line_width(0.05)
            nx, ny = -(sy1 - p0[1]), (sx1 - p0[0]); nl = math.hypot(nx, ny) or 1
            cr.move_to(sx1 - nx / nl * lw * 0.88, sy1 - ny / nl * lw * 0.88); cr.line_to(sx1 + nx / nl * lw * 0.88, sy1 + ny / nl * lw * 0.88); cr.stroke()
        col(cr, skin); cr.arc(p2[0], p2[1], lw * 0.75, 0, 2 * math.pi); cr.fill()
        if key in ("grandma", "woman"):
            col(cr, s["trim"]); cr.set_line_width(0.05)
            ellipse(cr, p2[0] - (p2[0] - p1[0]) * 0.18, p2[1] - (p2[1] - p1[1]) * 0.18, lw * 0.62, lw * 0.25,
                    math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + math.pi / 2); cr.stroke()
        rig.shoulder[sx] = (x + p0[0] * R, y + p0[1] * R)
        rig.hand[sx] = (x + p2[0] * R, y + p2[1] * R)
    if p["hold"] != "behind":
        draw_arm(-1, p["armR"]); draw_arm(1, p["armL"])

    # ---------------- neck + head
    hx = lean + p["turn"] * 0.05
    col(cr, sk_d); rrect(cr, -0.2 + lean * 0.8, neckY - 0.1, 0.4, s["neck"] + 0.25, 0.1); cr.fill()
    cr.save()
    cr.translate(hx, headY + 0.85)
    cr.rotate(p["tilt"])
    cr.translate(0, -0.85)
    if p["back"]:
        draw_head_back(cr, key, s, p)
    else:
        draw_head(cr, key, s, p)
    cr.restore()
    rig.head = (x + hx * R, y + headY * R)
    rig.mouth = (x + (hx + p["turn"] * 0.3) * R, y + (headY + 0.6) * R)
    rig.hipY = y + hipY * R
    cr.restore()
    return rig


def draw_head(cr, key, s, p):
    skin = s["skin"]; sk_d = shade(skin, -0.2); sk_l = shade(skin, 0.15)
    t = p["turn"]; ry = s["headry"]
    hair = s["hair"]
    # back hair (bun / back of head)
    if s["style"] == "bun":
        col(cr, shade(hair, -0.15)); ellipse(cr, -t * 0.5 + 0.0, -0.75, 0.42, 0.36); cr.fill()
        col(cr, shade(hair, -0.05)); ellipse(cr, -t * 0.5, -0.8, 0.34, 0.28); cr.fill()
    elif s["style"] == "ponytail":
        sw_ = p["hair_sway"]
        bx = 0.62 - t * 0.5
        lin(cr, 0, -0.9, 0, 1.0, [(0, shade(hair, 0.08)), (1, shade(hair, -0.12))])
        cr.move_to(bx - 0.15, -0.85); cr.curve_to(bx + 0.6, -0.95, bx + 0.75 + sw_ * 0.3, -0.2, bx + 0.55 + sw_ * 0.5, 0.75)
        cr.curve_to(bx + 0.5 + sw_ * 0.5, 0.45, bx + 0.35 + sw_ * 0.3, 0.2, bx + 0.32 + sw_ * 0.2, 0.35)
        cr.curve_to(bx + 0.4, -0.1, bx + 0.25, -0.55, bx - 0.1, -0.6); cr.close_path(); cr.fill()
        col(cr, s["trim"]); ellipse(cr, bx + 0.12, -0.78, 0.1, 0.13, 0.5); cr.fill()
    elif s["style"] == "long":
        sw_ = p["hair_sway"]
        lin(cr, 0, -1.0, 0, 1.9, [(0, shade(hair, 0.05)), (1, shade(hair, -0.15))])
        cr.move_to(-1.05, -0.4); cr.curve_to(-1.2, 0.5, -1.25 + sw_ * 0.2, 1.3, -1.15 + sw_ * 0.3, 1.75)
        for k in range(7):   # pointed hair ends
            xx = -1.15 + k * 0.38 + sw_ * 0.3
            cr.line_to(xx + 0.19, 1.55 + 0.05 * (k % 2)); cr.line_to(xx + 0.38, 1.8 - 0.06 * (k % 3))
        cr.curve_to(1.25 + sw_ * 0.2, 1.3, 1.2, 0.5, 1.05, -0.4)
        cr.curve_to(1.0, -1.0, -1.0, -1.0, -1.05, -0.4); cr.close_path(); cr.fill()
    # ears
    for sx in (-1, 1):
        ex = sx * 0.97 - t * 0.18
        if (sx < 0 and t > 0.55) or (sx > 0 and t < -0.55):
            continue
        col(cr, sk_d); ellipse(cr, ex, 0.08, 0.17, 0.24); cr.fill()
        col(cr, shade(skin, -0.35)); ellipse(cr, ex + sx * -0.03, 0.08, 0.07, 0.13); cr.fill()
        if key in ("grandma", "woman", "girl"):
            col(cr, s["trim"] if key != "girl" else "#e0b04a"); cr.arc(ex, 0.33, 0.07 if key != "girl" else 0.05, 0, 2 * math.pi); cr.fill()
    # face
    rad(cr, -0.3 + t * 0.2, -0.35, 0.1, 1.35, [(0, sk_l), (0.55, skin), (1, sk_d)])
    if ANIME and key != "child":   # slimmer anime jaw with a soft pointed chin
        ch = ry * (1.06 if s.get("old") else 1.1)
        cr.move_to(0, -ry); cr.curve_to(0.62, -ry, 0.98, -0.62, 0.98, -0.05)
        cr.curve_to(0.96, 0.4, 0.42, ch * 0.92, 0, ch)
        cr.curve_to(-0.42, ch * 0.92, -0.96, 0.4, -0.98, -0.05)
        cr.curve_to(-0.98, -0.62, -0.62, -ry, 0, -ry); cr.close_path(); cr.fill()
    elif key in ("child", "girl"):
        cr.move_to(0, -ry); cr.curve_to(0.62, -ry, 1.0, -0.6, 1.0, -0.05)
        cr.curve_to(1.0, 0.55, 0.62, ry * 0.95, 0, ry * 0.95)
        cr.curve_to(-0.62, ry * 0.95, -1.0, 0.55, -1.0, -0.05)
        cr.curve_to(-1.0, -0.6, -0.62, -ry, 0, -ry); cr.close_path(); cr.fill()
    else:
        cr.move_to(0, -ry); cr.curve_to(0.62, -ry, 0.98, -0.62, 0.98, -0.05)
        cr.curve_to(0.98, 0.55, 0.62, ry * 1.0, 0, ry * 1.02)
        cr.curve_to(-0.62, ry * 1.0, -0.98, 0.55, -0.98, -0.05)
        cr.curve_to(-0.98, -0.62, -0.62, -ry, 0, -ry); cr.close_path(); cr.fill()
    # cheeks blush
    young = key in ("child", "girl", "woman")
    for sx in (-1, 1):
        bx_ = sx * 0.55 + t * 0.25
        if ANIME:
            col(cr, (0.95, 0.42, 0.45, 0.32 if young else 0.16)); ellipse(cr, bx_, 0.36, 0.24, 0.12); cr.fill()
            if young:
                col(cr, (0.85, 0.3, 0.35, 0.55)); cr.set_line_width(0.025); cr.set_line_cap(cairo.LINE_CAP_ROUND)
                for k in range(3):
                    cr.move_to(bx_ - 0.12 + k * 0.09, 0.42); cr.line_to(bx_ - 0.07 + k * 0.09, 0.3); cr.stroke()
            continue
        rad(cr, bx_, 0.38, 0, 0.28, [(0, (0.85, 0.35, 0.3, 0.28 if young else 0.18)), (1, (0.85, 0.35, 0.3, 0))])
        cr.arc(bx_, 0.38, 0.28, 0, 2 * math.pi); cr.fill()
    # eyes
    e = s["eye"]
    blink = max(p["blink"], p["sleepy"])
    gx, gy = p["gaze"]
    for sx in (-1, 1):
        ex = sx * 0.37 * (1 - 0.18 * abs(t) * (1 if sx * t < 0 else 0.3)) + t * 0.3
        ey = 0.02
        rx = 0.21 * e * (1 - 0.25 * max(0, -sx * t)); ry_ = 0.26 * e
        if ANIME:
            ex = sx * 0.4 * (1 - 0.18 * abs(t) * (1 if sx * t < 0 else 0.3)) + t * 0.3; ey = 0.06
            rx = 0.25 * e * (1 - 0.3 * max(0, -sx * t)); ry_ = (0.33 if young else 0.24) * e
            if s.get("old"):
                ry_ *= 0.8
        if p["happy_eyes"] and blink > 0.5:
            col(cr, "#2a1810"); cr.set_line_width(0.065); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc_negative(ex, ey + 0.12, rx * 0.95, -0.2, -math.pi + 0.2); cr.stroke()
            continue
        if blink > 0.92:
            col(cr, "#2a1810"); cr.set_line_width(0.055); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc(ex, ey - 0.06, rx * 1.0, 0.25, math.pi - 0.25); cr.stroke()
            continue
        if ANIME:
            anime_eye(cr, s, p, ex, ey, rx, ry_, sx, e, blink, gx, gy)
            continue
        cr.save()
        ellipse(cr, ex, ey, rx, ry_); cr.clip()
        col(cr, "#fbf8f1"); cr.paint()
        ix, iy = ex + gx * rx * 0.45, ey + gy * ry_ * 0.35 + 0.02
        rad(cr, ix, iy, 0, 0.16 * e, [(0, shade(s["iris"], 0.25)), (1, s["iris"])])
        cr.arc(ix, iy, 0.16 * e, 0, 2 * math.pi); cr.fill()
        col(cr, "#0b0705"); cr.arc(ix, iy, 0.085 * e, 0, 2 * math.pi); cr.fill()
        col(cr, "#ffffff"); cr.arc(ix - 0.05 * e, iy - 0.06 * e, 0.045 * e, 0, 2 * math.pi); cr.fill()
        cr.arc(ix + 0.05 * e, iy + 0.05 * e, 0.02 * e, 0, 2 * math.pi); cr.fill()
        # eyelid
        if blink > 0:
            col(cr, shade(skin, -0.05)); cr.rectangle(ex - 1, ey - ry_ - 0.01, 2, 2 * ry_ * blink); cr.fill()
        cr.restore()
        col(cr, "#22140c"); cr.set_line_width(0.05); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        ly = ey - ry_ + 2 * ry_ * blink
        cr.save(); cr.translate(ex, ey); cr.scale(rx, ry_)
        a0 = math.pi + 0.15; a1 = 2 * math.pi - 0.15
        if blink > 0:
            cr.restore(); cr.move_to(ex - rx, ly); cr.line_to(ex + rx, ly); cr.stroke()
        else:
            cr.arc(0, 0, 1.02, a0, a1); cr.restore(); cr.stroke()
        if s.get("old"):
            col(cr, shade(skin, -0.32)); cr.set_line_width(0.025)
            for k in range(2):
                cr.move_to(ex + sx * (rx + 0.03), ey + 0.02 + k * 0.07); cr.line_to(ex + sx * (rx + 0.12), ey - 0.02 + k * 0.1); cr.stroke()
    # brows
    bcol = "#1a110b" if s["style"] in ("kid", "adult") else shade(s["hair"], -0.25)
    col(cr, bcol); cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx in (-1, 1):
        bx = sx * 0.37 + t * 0.32; by = -0.32 - 0.09 * p["brows"]
        cr.set_line_width(0.085 if key in ("child", "adult") else 0.075)
        if ANIME:
            bx = sx * 0.42 + t * 0.32; by = -0.36 - 0.1 * p["brows"] - (0.06 if young else 0)
            cr.set_line_width(0.05 if s.get("lashes") else 0.07)
        cr.move_to(bx - sx * 0.17, by + 0.0); cr.curve_to(bx - sx * 0.07, by - 0.07, bx + sx * 0.08, by - 0.07, bx + sx * 0.19, by + 0.04); cr.stroke()
    # nose
    nx = t * 0.42
    if ANIME:   # anime nose: a tiny shadow tick
        col(cr, shade(skin, -0.3)); cr.set_line_width(0.04); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(nx + 0.03, 0.24); cr.line_to(nx - 0.03, 0.34); cr.stroke()
    else:
        col(cr, shade(skin, -0.25)); cr.set_line_width(0.045)
        cr.move_to(nx - 0.08, 0.3); cr.curve_to(nx - 0.04, 0.36, nx + 0.04, 0.36, nx + 0.08, 0.3); cr.stroke()
        rad(cr, nx - 0.03, 0.22, 0, 0.13, [(0, shade(skin, 0.18)), (1, (1, 1, 1, 0))]); cr.arc(nx - 0.03, 0.22, 0.13, 0, 6.3); cr.fill()
    # moustache
    mx = t * 0.33
    if s["style"] == "bald":
        col(cr, shade(s["hair"], -0.08))
        cr.move_to(mx, 0.44); cr.curve_to(mx - 0.15, 0.36, mx - 0.38, 0.4, mx - 0.4, 0.55); cr.curve_to(mx - 0.25, 0.5, mx - 0.12, 0.54, mx, 0.5)
        cr.curve_to(mx + 0.12, 0.54, mx + 0.25, 0.5, mx + 0.4, 0.55); cr.curve_to(mx + 0.38, 0.4, mx + 0.15, 0.36, mx, 0.44); cr.close_path(); cr.fill()
    # mouth
    m = p["mouth"]; sm = p["smile"]
    my = 0.6 if not ANIME else 0.58
    if m > 0.05:
        w_ = (0.17 + 0.05 * sm + 0.03 * m) * (0.78 if ANIME else 1); h_ = 0.05 + 0.22 * m
        col(cr, "#4a1410")
        cr.move_to(mx - w_, my); cr.curve_to(mx - w_ * 0.6, my - 0.03 * sm, mx + w_ * 0.6, my - 0.03 * sm, mx + w_, my)
        cr.curve_to(mx + w_ * 0.8, my + h_, mx - w_ * 0.8, my + h_, mx - w_, my); cr.close_path(); cr.fill()
        cr.save(); cr.move_to(mx - w_, my); cr.curve_to(mx - w_ * 0.6, my - 0.03 * sm, mx + w_ * 0.6, my - 0.03 * sm, mx + w_, my)
        cr.curve_to(mx + w_ * 0.8, my + h_, mx - w_ * 0.8, my + h_, mx - w_, my); cr.close_path(); cr.clip()
        col(cr, "#c9545a"); ellipse(cr, mx, my + h_ * 0.95, w_ * 0.6, h_ * 0.45); cr.fill()
        if key != "grandpa" and m > 0.3:
            col(cr, "#f6f1ea"); cr.rectangle(mx - w_, my - 0.05, 2 * w_, 0.07); cr.fill()
        cr.restore()
    else:
        col(cr, "#5a2418"); cr.set_line_width(0.05); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        w_ = (0.16 + 0.06 * sm) * (0.7 if ANIME else 1)
        cr.move_to(mx - w_, my - 0.03 * sm); cr.curve_to(mx - w_ * 0.5, my + 0.1 * sm, mx + w_ * 0.5, my + 0.1 * sm, mx + w_, my - 0.03 * sm); cr.stroke()
    if s["style"] == "adult" and not (ANIME and s.get("old")):
        rad(cr, mx, 0.72, 0, 0.55, [(0, (0.15, 0.08, 0.05, 0.22)), (0.6, (0.15, 0.08, 0.05, 0.12)), (1, (0.15, 0.08, 0.05, 0))])
        ellipse(cr, mx, 0.72, 0.62, 0.35); cr.fill()
        col(cr, s.get("mous", "#22140c")); cr.move_to(mx, 0.48); cr.curve_to(mx - 0.12, 0.43, mx - 0.28, 0.46, mx - 0.3, 0.53); cr.curve_to(mx - 0.15, 0.5, mx, 0.53, mx, 0.53)
        cr.curve_to(mx, 0.53, mx + 0.15, 0.5, mx + 0.3, 0.53); cr.curve_to(mx + 0.28, 0.46, mx + 0.12, 0.43, mx, 0.48); cr.fill()
    # front hair
    hl = shade(hair, 0.25)
    if ANIME and s["style"] in ("kid", "adult", "ponytail", "long"):
        anime_fringe(cr, s, p, t, ry)
    elif s["style"] in ("ponytail", "long"):
        anime_fringe(cr, s, p, t, ry)
    elif s["style"] in ("kid", "adult"):
        lin(cr, 0, -1.1, 0, -0.2, [(0, shade(hair, 0.12)), (1, hair)])
        top = -ry - 0.12 if s["style"] == "kid" else -ry - 0.16
        cr.move_to(-1.03, -0.05)
        cr.curve_to(-1.12, -0.7, -0.6, top, 0.05, top)
        cr.curve_to(0.7, top, 1.12, -0.7, 1.03, -0.05)
        cr.curve_to(0.98, -0.25, 0.9, -0.38, 0.8, -0.42)
        # fringe sweeping to one side
        fr = [(0.62, -0.38), (0.4, -0.52), (0.25, -0.4), (0.0, -0.55), (-0.2, -0.42), (-0.45, -0.56), (-0.62, -0.4), (-0.8, -0.45)] if s["style"] == "kid" else \
             [(0.62, -0.5), (0.3, -0.62), (0.0, -0.6), (-0.3, -0.66), (-0.7, -0.5)]
        for (fx, fy) in fr:
            cr.line_to(fx + t * 0.15, fy)
        cr.curve_to(-0.92, -0.38, -0.98, -0.25, -1.03, -0.05); cr.close_path(); cr.fill()
        col(cr, (*rgb(hl)[:3], 0.55)); cr.set_line_width(0.06); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(-0.5, -0.9); cr.curve_to(-0.2, -1.02, 0.2, -1.02, 0.45, -0.92); cr.stroke()
        if s["style"] == "kid":
            col(cr, hair); cr.move_to(0.05, top + 0.02); cr.curve_to(0.15, top - 0.2, 0.3, top - 0.18, 0.35, top - 0.12); cr.curve_to(0.25, top - 0.08, 0.18, top, 0.2, top + 0.05); cr.fill()
    elif s["style"] == "bun":
        lin(cr, 0, -1.1, 0, -0.1, [(0, shade(hair, 0.1)), (1, shade(hair, -0.1))])
        cr.move_to(-1.0, 0.05); cr.curve_to(-1.1, -0.75, -0.55, -ry - 0.1, 0, -ry - 0.08)
        cr.curve_to(0.55, -ry - 0.1, 1.1, -0.75, 1.0, 0.05)
        cr.curve_to(0.92, -0.2, 0.75, -0.45, 0.4, -0.55); cr.curve_to(0.2, -0.6, 0.05, -0.62, 0.0, -0.66)
        cr.curve_to(-0.05, -0.62, -0.2, -0.6, -0.4, -0.55); cr.curve_to(-0.75, -0.45, -0.92, -0.2, -1.0, 0.05); cr.close_path(); cr.fill()
        col(cr, shade(hair, -0.3)); cr.set_line_width(0.03)
        for k in (-0.5, -0.25, 0.25, 0.5):
            cr.move_to(k * 0.4, -0.66); cr.curve_to(k * 1.2, -0.75, k * 1.7, -0.5, k * 1.85, -0.15); cr.stroke()
        col(cr, "#a3121d"); cr.arc(t * 0.35, -0.36, 0.06, 0, 2 * math.pi); cr.fill()   # bindi
    elif s["style"] == "bald":
        # shiny head + grey hair on the sides
        rad(cr, -0.25, -0.75, 0, 0.35, [(0, (1, 1, 1, 0.28)), (1, (1, 1, 1, 0))]); cr.arc(-0.25, -0.75, 0.35, 0, 6.3); cr.fill()
        for sx in (-1, 1):
            if (sx < 0 and t > 0.6) or (sx > 0 and t < -0.6):
                continue
            col(cr, hair)
            bx = sx * 0.95 - t * 0.12
            cr.move_to(bx, 0.15); cr.curve_to(bx + sx * 0.12, -0.1, bx + sx * 0.1, -0.45, bx - sx * 0.12, -0.6)
            cr.curve_to(bx - sx * 0.22, -0.45, bx - sx * 0.15, -0.1, bx - sx * 0.1, 0.15); cr.close_path(); cr.fill()
        col(cr, shade(skin, -0.3)); cr.set_line_width(0.025)
        for k in range(2):
            cr.move_to(-0.35 + t * 0.3, -0.62 - k * 0.1); cr.curve_to(-0.1, -0.67 - k * 0.1, 0.1, -0.67 - k * 0.1, 0.35 + t * 0.3, -0.62 - k * 0.1); cr.stroke()
        # round spectacles
        col(cr, "#3b2616"); cr.set_line_width(0.045)
        for sx in (-1, 1):
            ex = sx * 0.37 * (1 - 0.1 * abs(t)) + t * 0.3
            cr.arc(ex, 0.02, 0.27, 0, 2 * math.pi); cr.stroke()
            rad(cr, ex - 0.08, -0.08, 0, 0.27, [(0, (1, 1, 1, 0.22)), (1, (1, 1, 1, 0.02))]); cr.arc(ex, 0.02, 0.26, 0, 2 * math.pi); cr.fill()
            col(cr, "#3b2616")
        cr.move_to(-0.1 + t * 0.3, 0.0); cr.curve_to(-0.04 + t * 0.3, -0.05, 0.04 + t * 0.3, -0.05, 0.1 + t * 0.3, 0.0); cr.stroke()


def anime_eye(cr, s, p, ex, ey, rx, ry_, sx, e, blink, gx, gy):
    """big glossy anime eye: gradient iris, pupil, two highlights, heavy upper lash line"""
    skin = s["skin"]; iris = s["iris"]; iris2 = s.get("iris2", mix(iris, "#d0913f", 0.65))
    young = s.get("lashes") or s["style"] in ("kid", "ponytail")
    cr.save()
    ellipse(cr, ex, ey, rx, ry_); cr.clip()
    col(cr, "#fffdf8"); cr.paint()
    ix, iy = ex + gx * rx * 0.32, ey + gy * ry_ * 0.22 + 0.03 * e
    irx, iry = rx * 0.8, ry_ * 0.9
    lin(cr, 0, iy - iry, 0, iy + iry, [(0, shade(iris, -0.55)), (0.5, iris), (1, iris2)])
    ellipse(cr, ix, iy, irx, iry); cr.fill()
    col(cr, shade(iris, -0.75)); ellipse(cr, ix, iy - iry * 0.05, irx * 0.48, iry * 0.52); cr.fill()
    col(cr, (*rgb(iris2)[:3], 0.55)); ellipse(cr, ix, iy + iry * 0.6, irx * 0.6, iry * 0.22); cr.fill()
    lin(cr, 0, ey - ry_, 0, ey - ry_ * 0.2, [(0, (0.25, 0.12, 0.18, 0.5)), (1, (0.25, 0.12, 0.18, 0))])
    cr.rectangle(ex - 1, ey - ry_, 2, ry_); cr.fill()
    col(cr, "#ffffff")
    ellipse(cr, ix - irx * 0.36, iy - iry * 0.4, irx * 0.36, iry * 0.27, -0.5); cr.fill()
    cr.arc(ix + irx * 0.4, iy + iry * 0.38, irx * 0.14, 0, 2 * math.pi); cr.fill()
    if p["tears"] > 0:   # welling tears: glossy waterline
        col(cr, (0.75, 0.9, 1.0, 0.55 * p["tears"])); ellipse(cr, ex, ey + ry_ * 0.75, rx * 0.95, ry_ * 0.35); cr.fill()
    if blink > 0:
        col(cr, shade(skin, -0.05)); cr.rectangle(ex - 1, ey - ry_ - 0.01, 2, 2 * ry_ * blink); cr.fill()
    cr.restore()
    ink = (0.13, 0.07, 0.08, 1)
    col(cr, ink); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if blink > 0:
        ly = ey - ry_ + 2 * ry_ * blink
        cr.set_line_width(0.07); cr.move_to(ex - rx * 1.05, ly); cr.curve_to(ex - rx * 0.4, ly + 0.03 * blink, ex + rx * 0.4, ly + 0.03 * blink, ex + rx * 1.05, ly); cr.stroke()
    else:
        # thick upper lid, thicker toward the outer corner
        cr.save(); cr.translate(ex, ey); cr.scale(rx, ry_)
        cr.arc(0, 0, 1.04, math.pi + 0.12, 2 * math.pi - 0.12); cr.restore()
        cr.set_line_width(0.085); cr.stroke()
        ox, oy = ex + sx * rx * 0.98, ey - ry_ * 0.25
        cr.move_to(ox - sx * rx * 0.3, ey - ry_ * 0.95); cr.line_to(ox + sx * rx * 0.32, oy - ry_ * 0.35)
        cr.line_to(ox, oy + 0.02); cr.close_path(); cr.fill()
        if young:
            cr.set_line_width(0.035)
            cr.move_to(ox, oy - ry_ * 0.2); cr.line_to(ox + sx * rx * 0.35, oy - ry_ * 0.05); cr.stroke()
        # lower lid hint
        col(cr, (*ink[:3], 0.55)); cr.set_line_width(0.03)
        cr.save(); cr.translate(ex, ey); cr.scale(rx, ry_)
        a0, a1 = (0.25, 1.1) if sx > 0 else (math.pi - 1.1, math.pi - 0.25)
        cr.arc(0, 0, 1.0, a0, a1); cr.restore(); cr.stroke()
    if p["tears"] > 0.05:   # streams down the cheek
        tl = p["tears"]
        tx = ex + sx * rx * 0.55
        lin(cr, 0, ey + ry_ * 0.8, 0, ey + ry_ + 0.55 * tl, [(0, (0.7, 0.88, 1.0, 0.85)), (1, (0.7, 0.88, 1.0, 0.25))])
        cr.move_to(tx - 0.04, ey + ry_ * 0.8); cr.curve_to(tx - 0.05, ey + ry_ + 0.2 * tl, tx + sx * 0.03, ey + ry_ + 0.4 * tl, tx + sx * 0.02, ey + ry_ + 0.55 * tl)
        cr.line_to(tx + sx * 0.08, ey + ry_ + 0.5 * tl); cr.curve_to(tx + 0.05, ey + ry_ + 0.3 * tl, tx + 0.05, ey + ry_ * 1.0, tx + 0.04, ey + ry_ * 0.8)
        cr.close_path(); cr.fill()
        col(cr, (1, 1, 1, 0.8)); cr.arc(tx + sx * 0.04, ey + ry_ + 0.5 * tl, 0.035, 0, 2 * math.pi); cr.fill()


def anime_fringe(cr, s, p, t, ry):
    """hair cap with sharp pointed bangs, side locks and a glossy 'angel ring'"""
    hair = s["hair"]; st = s["style"]
    hl = shade(hair, 0.35) if sum(rgb(hair)[:3]) < 1.5 else shade(hair, 0.5)
    top = -ry - (0.14 if st == "kid" else 0.17)
    if st in ("ponytail", "long"):   # side locks framing the face
        for sx in (-1, 1):
            if (sx < 0 and t > 0.6) or (sx > 0 and t < -0.6):
                continue
            bx = sx * 0.98 - t * 0.12
            ln = 0.75 if st == "ponytail" else 1.15
            lin(cr, 0, -0.5, 0, ln, [(0, hair), (1, shade(hair, -0.1))])
            cr.move_to(bx + sx * 0.08, -0.45); cr.curve_to(bx + sx * 0.12, 0.0, bx + sx * 0.02, ln * 0.6, bx - sx * 0.08, ln)
            cr.curve_to(bx - sx * 0.12, ln * 0.55, bx - sx * 0.18, 0.1, bx - sx * 0.25, -0.35); cr.close_path(); cr.fill()
    lin(cr, 0, -1.15, 0, -0.2, [(0, shade(hair, 0.1)), (1, hair)])
    cr.move_to(-1.05, 0.0)
    cr.curve_to(-1.13, -0.72, -0.6, top, 0.05, top)
    cr.curve_to(0.7, top, 1.13, -0.72, 1.05, 0.0)
    if st == "kid":
        bangs = [(0.92, -0.3), (0.75, -0.62), (0.6, -0.42), (0.42, -0.68), (0.22, -0.46), (0.05, -0.72), (-0.15, -0.48),
                 (-0.32, -0.7), (-0.52, -0.44), (-0.68, -0.64), (-0.9, -0.28)]
    elif st == "adult":
        bangs = [(0.95, -0.3), (0.75, -0.66), (0.5, -0.45), (0.25, -0.72), (-0.05, -0.5), (-0.3, -0.74), (-0.6, -0.5), (-0.78, -0.68), (-0.95, -0.3)]
    elif st == "ponytail":
        bangs = [(0.88, -0.2), (0.72, -0.6), (0.55, -0.42), (0.35, -0.66), (0.14, -0.46), (0.0, -0.72), (-0.16, -0.46),
                 (-0.38, -0.66), (-0.58, -0.42), (-0.74, -0.6), (-0.9, -0.18)]
    else:   # long: centre-parted curtain bangs
        bangs = [(0.9, -0.1), (0.72, -0.48), (0.55, -0.36), (0.35, -0.6), (0.12, -0.5), (0.0, -0.74), (-0.12, -0.5),
                 (-0.35, -0.6), (-0.55, -0.36), (-0.72, -0.48), (-0.9, -0.1)]
    for (bx, by) in bangs:
        cr.line_to(bx + t * 0.15 * (1 + by), by)
    cr.close_path(); cr.fill()
    # angel ring highlight
    col(cr, (*rgb(hl)[:3], 0.3)); cr.set_line_width(0.06); cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(-0.6 + t * 0.2, -0.82); cr.curve_to(-0.3 + t * 0.2, -0.96, 0.3 + t * 0.2, -0.96, 0.6 + t * 0.2, -0.82); cr.stroke()
    if st == "kid":
        col(cr, hair); cr.move_to(0.05, top + 0.02); cr.curve_to(0.15, top - 0.25, 0.32, top - 0.22, 0.4, top - 0.18); cr.curve_to(0.25, top - 0.08, 0.18, top, 0.2, top + 0.05); cr.fill()


def umbrella(cr, hx, hy, size, tilt=0.0, c="#1d1b22", open_=1.0, worn=False):
    """umbrella held at hand (hx, hy): shaft up, dome canopy; size = canopy radius"""
    cr.save(); cr.translate(hx, hy); cr.rotate(tilt)
    L = size * 1.25
    col(cr, "#3a2a1c"); cr.set_line_width(size * 0.035); cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(0, size * 0.12); cr.line_to(0, -L); cr.stroke()
    cr.arc_negative(-size * 0.08, size * 0.12, size * 0.08, 0, math.pi); cr.stroke()   # J handle
    w = size * (0.35 + 0.65 * open_); hgt = size * (0.55 + 0.1 * (1 - open_))
    lin(cr, -w, 0, w, 0, [(0, shade(c, -0.15)), (0.45, shade(c, 0.12)), (1, shade(c, -0.25))])
    cr.move_to(-w, -L + hgt * 0.75)
    cr.curve_to(-w * 0.9, -L - hgt * 0.55, w * 0.9, -L - hgt * 0.55, w, -L + hgt * 0.75)
    n = 8
    for k in range(n, 0, -1):   # scalloped rim between ribs
        x1 = -w + 2 * w * (k - 1) / n; xm = -w + 2 * w * (k - 0.5) / n
        cr.curve_to(-w + 2 * w * (k - 0.75) / n, -L + hgt * 0.62, xm, -L + hgt * 0.6, x1, -L + hgt * 0.75 - (0.02 * size if worn and k == 3 else 0))
    cr.close_path(); cr.fill()
    col(cr, shade(c, -0.35)); cr.set_line_width(size * 0.015)
    for k in range(1, n):
        x1 = -w + 2 * w * k / n
        cr.move_to(0, -L - hgt * 0.4); cr.curve_to(x1 * 0.5, -L - hgt * 0.3, x1 * 0.9, -L, x1, -L + hgt * 0.72); cr.stroke()
    col(cr, (1, 1, 1, 0.18)); cr.set_line_width(size * 0.05)
    cr.arc(0, -L + hgt * 0.4, w * 0.78, math.pi + 0.5, math.pi + 1.2); cr.stroke()
    col(cr, "#c9b48a"); cr.arc(0, -L - hgt * 0.42, size * 0.035, 0, 6.3); cr.fill()
    cr.restore()
    return (hx + math.sin(tilt) * L, hy - math.cos(tilt) * L)


def draw_lying_child(cr, x, y, R, blanket="#c4553a", **pose):
    """child asleep in bed, seen from the foot of the bed: head on pillow, blanket up to the chest"""
    p = dict(DEFAULT); p.update(pose)
    s = SPEC["child"]
    cr.save(); cr.translate(x, y); cr.scale(R, R)
    # head
    cr.save(); cr.translate(0, -0.2); cr.rotate(p["tilt"])
    draw_head(cr, "child", s, p)
    cr.restore()
    # shoulders + blanket mound (foreshortened)
    lin(cr, 0, 0.6, 0, 1.8, [(0, shade(s["top"], -0.05)), (1, shade(s["top"], -0.3))])
    ellipse(cr, 0, 0.95, 0.95, 0.3); cr.fill()
    cr.restore()


def draw_blanket(cr, x, y, R, w, h, c1="#c4553a", c2="#f0e2c6"):
    """checked cotton blanket mound"""
    cr.save(); cr.translate(x, y); cr.scale(R, R)
    cr.move_to(-w, h); cr.curve_to(-w * 1.05, h * 0.3, -w * 0.8, 0.0, -w * 0.4, 0.02)
    cr.curve_to(-w * 0.1, -0.08, w * 0.1, -0.08, w * 0.4, 0.02)
    cr.curve_to(w * 0.8, 0.0, w * 1.05, h * 0.3, w, h); cr.close_path()
    cr.save(); cr.clip()
    col(cr, c2); cr.paint()
    col(cr, (*rgb(c1)[:3], 0.75)); cr.set_line_width(0.09)
    for k in range(-12, 13):
        cr.move_to(k * 0.22, -1); cr.line_to(k * 0.22 + 0.5, h + 1); cr.stroke()
    col(cr, (*rgb(c1)[:3], 0.45))
    for k in range(0, 14):
        cr.move_to(-w - 1, k * 0.22); cr.line_to(w + 1, k * 0.22 - 0.2); cr.stroke()
    lin(cr, 0, 0, 0, h, [(0, (0, 0, 0, 0)), (1, (0, 0, 0, 0.35))]); cr.paint()
    rad(cr, -w * 0.4, 0.1, 0, w, [(0, (1, 1, 1, 0.18)), (1, (1, 1, 1, 0))]); cr.paint()
    cr.restore(); cr.restore()


def draw_head_back(cr, key, s, p):
    skin = s["skin"]; ry = s["headry"]
    for sx in (-1, 1):
        col(cr, shade(skin, -0.2)); ellipse(cr, sx * 0.97, 0.08, 0.17, 0.24); cr.fill()
    col(cr, shade(skin, -0.1)); ellipse(cr, 0, 0.0, 0.98, ry); cr.fill()
    hair = s["hair"]
    lin(cr, 0, -1.1, 0, 0.8, [(0, shade(hair, 0.12)), (1, shade(hair, -0.1))])
    if s["style"] == "bald":
        cr.move_to(-0.98, 0.3); cr.curve_to(-1.0, -0.2, -0.6, -0.3, 0, -0.3); cr.curve_to(0.6, -0.3, 1.0, -0.2, 0.98, 0.3)
        cr.curve_to(0.7, 0.75, -0.7, 0.75, -0.98, 0.3); cr.close_path(); cr.fill()
    else:
        cr.move_to(-1.03, 0.2); cr.curve_to(-1.1, -0.75, -0.6, -ry - 0.12, 0, -ry - 0.12)
        cr.curve_to(0.6, -ry - 0.12, 1.1, -0.75, 1.03, 0.2)
        cr.curve_to(0.9, 0.7, -0.9, 0.7, -1.03, 0.2); cr.close_path(); cr.fill()
        if s["style"] == "bun":
            col(cr, shade(hair, -0.1)); ellipse(cr, 0, -0.1, 0.38, 0.32); cr.fill()
        elif s["style"] == "ponytail":
            sw_ = p["hair_sway"]
            col(cr, shade(hair, -0.05))
            cr.move_to(-0.25, -0.35); cr.curve_to(-0.35 + sw_ * 0.2, 0.4, -0.2 + sw_ * 0.4, 1.0, 0.05 + sw_ * 0.5, 1.45)
            cr.curve_to(0.3 + sw_ * 0.4, 1.0, 0.35 + sw_ * 0.2, 0.4, 0.25, -0.35); cr.close_path(); cr.fill()
            col(cr, s["trim"]); ellipse(cr, 0, -0.38, 0.2, 0.1); cr.fill()
        elif s["style"] == "long":
            sw_ = p["hair_sway"]
            cr.move_to(-1.03, 0.0); cr.curve_to(-1.15, 0.8, -1.1 + sw_ * 0.2, 1.4, -1.0 + sw_ * 0.3, 1.8)
            cr.curve_to(-0.3, 1.9, 0.3, 1.9, 1.0 + sw_ * 0.3, 1.8); cr.curve_to(1.1 + sw_ * 0.2, 1.4, 1.15, 0.8, 1.03, 0.0)
            cr.close_path(); cr.fill()
