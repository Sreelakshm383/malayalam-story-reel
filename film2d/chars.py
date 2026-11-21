"""2D illustrated characters (front / three-quarter view), soft-shaded cartoon style.

Every character is drawn by draw_person() from a fixed SPEC, so face, hair,
clothes, proportions and colours never change between scenes.
Units: R = head radius in px. (x, y) = point between the feet on the ground.
"""
import math
import cairo
from draw import rgb, shade, mix, col, lin, rad, ellipse, rrect, smooth, limb, shadow, glow

SPEC = {
    "child": dict(R=1.0, torso=1.55, legs=1.75, arm=(0.85, 0.8), sw=0.78, ww=0.72, limb=0.24, neck=0.12,
                  skin="#b67a4f", hair="#1c1410", style="kid", eye=1.3, top="#f4b82e", trim="#e2622a",
                  bottom="#1f8c87", clothes="kid", iris="#3d2414", headry=1.0),
    "grandma": dict(R=1.0, torso=2.35, legs=3.0, arm=(1.25, 1.15), sw=1.18, ww=1.18, limb=0.26, neck=0.2,
                    skin="#a46c47", hair="#cfcac3", style="bun", eye=1.08, top="#8a2131", trim="#d6a53a",
                    bottom="#f4eddc", clothes="saree", iris="#2e1c10", headry=1.04),
    "grandpa": dict(R=1.0, torso=2.5, legs=3.3, arm=(1.32, 1.2), sw=1.2, ww=1.15, limb=0.26, neck=0.22,
                    skin="#956243", hair="#dedad3", style="bald", eye=1.02, top="#f1e9d6", trim="#d6a53a",
                    bottom="#f8f5ee", clothes="mundu", iris="#2e1c10", headry=1.07),
    "adult": dict(R=1.0, torso=2.5, legs=3.4, arm=(1.32, 1.22), sw=1.15, ww=0.98, limb=0.25, neck=0.24,
                  skin="#ae7650", hair="#1c1410", style="adult", eye=1.05, top="#eaa92c", trim="#e2622a",
                  bottom="#2f5d63", clothes="adult", iris="#3d2414", headry=1.08),
}

DEFAULT = dict(turn=0.0, tilt=0.0, mouth=0.0, smile=0.7, blink=0.0, gaze=(0.0, 0.0), brows=0.0, lean=0.0,
               armL=(8, 10), armR=(8, 10), legs="stand", happy_eyes=False, sleepy=0.0, body_turn=0.0,
               hold=None, bob=0.0, squash=0.0, back=False, alpha=1.0)


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

    if s["clothes"] in ("kid", "adult"):
        lc = skin if s["clothes"] == "kid" else s["bottom"]
        for i, sx in enumerate((-1, 1)):
            hx = sx * ww * 0.42
            if sitting:
                kx, ky = sx * ww * 0.5, hipY + 0.15
                fx, fy = sx * ww * 0.55, 0.0
                limb(cr, [(hx, hipY), (kx, ky)], lw * 1.35, shade(lc, -0.05))
                limb(cr, [(kx, ky), (fx, fy - 0.12)], lw * 1.2, lc)
                foot(fx, fy, sk_d if key == "child" else "#4a2e1d")
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
                else:
                    col(cr, "#4a2e1d"); ellipse(cr, fx, fy - 0.05, 0.27, 0.09); cr.fill()
                    foot(fx, fy - 0.02, sk_d)
        if s["clothes"] == "kid":   # shorts
            lin(cr, 0, hipY - 0.3, 0, hipY + 0.45, [(0, s["bottom"]), (1, shade(s["bottom"], -0.25))])
            cr.move_to(-ww * 0.98, hipY - 0.35); cr.line_to(ww * 0.98, hipY - 0.35)
            cr.line_to(ww * 1.02, hipY + 0.42); cr.line_to(0.06, hipY + 0.4); cr.line_to(0, hipY + 0.2)
            cr.line_to(-0.06, hipY + 0.4); cr.line_to(-ww * 1.02, hipY + 0.42); cr.close_path(); cr.fill()
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
    hemY = hipY + (0.55 if s["clothes"] == "kid" else (0.15 if s["clothes"] == "adult" else -0.1))
    if s["clothes"] == "saree":
        hemY = hipY - s["torso"] * 0.55
    lin(cr, -sw, 0, sw, 0, [(0, shade(top_c, -0.22)), (0.3 + 0.15 * bt, top_c), (0.65 + 0.15 * bt, shade(top_c, 0.08)), (1, shade(top_c, -0.25))])
    cr.move_to(-sw * 0.55, shY - 0.08)
    cr.curve_to(-sw * 0.95, shY - 0.05, -sw * 1.02, shY + 0.15, -sw * 1.0, shY + 0.4)
    cr.curve_to(-ww * 1.0, (shY + hemY) / 2, -ww * 1.02, hemY - 0.3, -ww * 1.02, hemY)
    cr.curve_to(-ww * 0.4, hemY + 0.06, ww * 0.4, hemY + 0.06, ww * 1.02, hemY)
    cr.curve_to(ww * 1.02, hemY - 0.3, ww * 1.0, (shY + hemY) / 2, sw * 1.0, shY + 0.4)
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
    if s["clothes"] in ("kid", "adult") and not p["back"]:
        col(cr, s["trim"])
        cr.move_to(-0.32, shY - 0.06); cr.curve_to(-0.2, shY + 0.2, 0.2, shY + 0.2, 0.32, shY - 0.06)
        cr.line_to(0.2, shY - 0.1); cr.curve_to(0.1, shY + 0.06, -0.1, shY + 0.06, -0.2, shY - 0.1); cr.close_path(); cr.fill()
        rrect(cr, -0.055, shY + 0.1, 0.11, 0.55 if key == "child" else 0.8, 0.04); cr.fill()
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
        sleeve = {"kid": 0.45, "saree": 0.4, "mundu": 0.55, "adult": 0.5}[s["clothes"]]
        limb(cr, [p0, p1, p2], lw * 1.25, sk_d if sx > 0 else skin, lw * 1.05)
        sx1 = p0[0] + (p1[0] - p0[0]) * sleeve; sy1 = p0[1] + (p1[1] - p0[1]) * sleeve
        limb(cr, [p0, (sx1, sy1)], lw * 1.75, shade(top_c, -0.08 if sx > 0 else 0.0))
        if s["clothes"] in ("kid", "saree"):
            col(cr, s["trim"]); cr.set_line_width(0.05)
            nx, ny = -(sy1 - p0[1]), (sx1 - p0[0]); nl = math.hypot(nx, ny) or 1
            cr.move_to(sx1 - nx / nl * lw * 0.88, sy1 - ny / nl * lw * 0.88); cr.line_to(sx1 + nx / nl * lw * 0.88, sy1 + ny / nl * lw * 0.88); cr.stroke()
        col(cr, skin); cr.arc(p2[0], p2[1], lw * 0.75, 0, 2 * math.pi); cr.fill()
        if key == "grandma":
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
    # ears
    for sx in (-1, 1):
        ex = sx * 0.97 - t * 0.18
        if (sx < 0 and t > 0.55) or (sx > 0 and t < -0.55):
            continue
        col(cr, sk_d); ellipse(cr, ex, 0.08, 0.17, 0.24); cr.fill()
        col(cr, shade(skin, -0.35)); ellipse(cr, ex + sx * -0.03, 0.08, 0.07, 0.13); cr.fill()
        if key == "grandma":
            col(cr, s["trim"]); cr.arc(ex, 0.33, 0.07, 0, 2 * math.pi); cr.fill()
    # face
    rad(cr, -0.3 + t * 0.2, -0.35, 0.1, 1.35, [(0, sk_l), (0.55, skin), (1, sk_d)])
    if key == "child":
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
    for sx in (-1, 1):
        rad(cr, sx * 0.55 + t * 0.25, 0.38, 0, 0.28, [(0, (0.85, 0.35, 0.3, 0.28 if key == "child" else 0.18)), (1, (0.85, 0.35, 0.3, 0))])
        cr.arc(sx * 0.55 + t * 0.25, 0.38, 0.28, 0, 2 * math.pi); cr.fill()
    # eyes
    e = s["eye"]
    blink = max(p["blink"], p["sleepy"])
    gx, gy = p["gaze"]
    for sx in (-1, 1):
        ex = sx * 0.37 * (1 - 0.18 * abs(t) * (1 if sx * t < 0 else 0.3)) + t * 0.3
        ey = 0.02
        rx = 0.21 * e * (1 - 0.25 * max(0, -sx * t)); ry_ = 0.26 * e
        if p["happy_eyes"] and blink > 0.5:
            col(cr, "#2a1810"); cr.set_line_width(0.065); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc_negative(ex, ey + 0.12, rx * 0.95, -0.2, -math.pi + 0.2); cr.stroke()
            continue
        if blink > 0.92:
            col(cr, "#2a1810"); cr.set_line_width(0.055); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc(ex, ey - 0.06, rx * 1.0, 0.25, math.pi - 0.25); cr.stroke()
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
        if key in ("grandma", "grandpa"):
            col(cr, shade(skin, -0.32)); cr.set_line_width(0.025)
            for k in range(2):
                cr.move_to(ex + sx * (rx + 0.03), ey + 0.02 + k * 0.07); cr.line_to(ex + sx * (rx + 0.12), ey - 0.02 + k * 0.1); cr.stroke()
    # brows
    bcol = "#1a110b" if s["style"] in ("kid", "adult") else shade(s["hair"], -0.25)
    col(cr, bcol); cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx in (-1, 1):
        bx = sx * 0.37 + t * 0.32; by = -0.32 - 0.09 * p["brows"]
        cr.set_line_width(0.085 if key in ("child", "adult") else 0.075)
        cr.move_to(bx - sx * 0.17, by + 0.0); cr.curve_to(bx - sx * 0.07, by - 0.07, bx + sx * 0.08, by - 0.07, bx + sx * 0.19, by + 0.04); cr.stroke()
    # nose
    nx = t * 0.42
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
    my = 0.6
    if m > 0.05:
        w_ = 0.17 + 0.05 * sm + 0.03 * m; h_ = 0.05 + 0.22 * m
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
        w_ = 0.16 + 0.06 * sm
        cr.move_to(mx - w_, my - 0.03 * sm); cr.curve_to(mx - w_ * 0.5, my + 0.1 * sm, mx + w_ * 0.5, my + 0.1 * sm, mx + w_, my - 0.03 * sm); cr.stroke()
    if s["style"] == "adult":
        rad(cr, mx, 0.72, 0, 0.55, [(0, (0.15, 0.08, 0.05, 0.22)), (0.6, (0.15, 0.08, 0.05, 0.12)), (1, (0.15, 0.08, 0.05, 0))])
        ellipse(cr, mx, 0.72, 0.62, 0.35); cr.fill()
        col(cr, "#22140c"); cr.move_to(mx, 0.48); cr.curve_to(mx - 0.12, 0.43, mx - 0.28, 0.46, mx - 0.3, 0.53); cr.curve_to(mx - 0.15, 0.5, mx, 0.53, mx, 0.53)
        cr.curve_to(mx, 0.53, mx + 0.15, 0.5, mx + 0.3, 0.53); cr.curve_to(mx + 0.28, 0.46, mx + 0.12, 0.43, mx, 0.48); cr.fill()
    # front hair
    hl = shade(hair, 0.25)
    if s["style"] in ("kid", "adult"):
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
