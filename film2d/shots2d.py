"""Shot list for the 2D illustrated version. Same timeline/voices as before.
frame(name, f) -> cairo ImageSurface 1080x1920"""
import math, random
import cairo
from draw import (W, H, rgb, shade, mix, col, lin, rad, ellipse, rrect, glow, shadow, new_surface, blurred_surface, lerp, ss)
import chars, scenes as S
from chars import draw_person, draw_blanket
from base import B, FPS, TL, META, SHOT, mouth, cue, blink, camera, cam_lerp, cached, paint_cached, _cache, render


# ------------------------------------------------------------------ shared sets
def far_day(cr, kind="gold", seed=4):
    S.sky(cr, kind, -900, 1050, -540, 1620, sun=(150, 560, 40, "#ffcf7a") if kind == "gold" else None)
    S.clouds(cr, 250, 0)
    S.treeline(cr, 1060, -540, 1620, c="#5d7a48" if kind != "dusk" else "#4a4a50", seed=seed)


def yard(cr, house_s=0.82, hy=1300, aged=0.0, kind="gold", door_open=True, night=False):
    H_ = S.house(cr, 540, hy, house_s, door_open=door_open, aged=aged, night=night)
    lin(cr, 0, hy, 0, 2900, [(0, "#d6b487"), (1, "#b48858")]); cr.rectangle(-540, hy, 2160, 1700); cr.fill()
    col(cr, (0, 0, 0, 0.08)); cr.rectangle(-540, hy, 2160, 18); cr.fill()
    S.bush(cr, 70, hy + 20, 70, seed=2, flowers="#c3121b"); S.bush(cr, 1010, hy + 20, 75, seed=3, flowers="#c3121b")
    # tulasi thara
    col(cr, "#f1e6cc" if not aged else "#b9ad94"); rrect(cr, 820, hy + 40, 90, 120, 8); cr.fill()
    col(cr, "#9a4a2b"); cr.rectangle(810, hy + 30, 110, 16); cr.fill()
    S.bush(cr, 865, hy + 30, 34, c="#3f7a2a", seed=8)
    return H_


# ------------------------------------------------------------------ shots
def sh_title(cr, t, shot):
    z, cx, cy = cam_lerp(t, 5, (1.0, 540, 780), (1.18, 540, 930))
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("far_gold", lambda c: far_day(c), blur=3))
    yard(cr)
    S.palm(cr, -40, 1500, 900, 0.12, 0.05 * math.sin(t * 1.2)); S.palm(cr, 1120, 1520, 950, -0.1, 0.05 * math.sin(t * 1.1 + 1))
    S.chaarukasera(cr, 540 - 330 * 0.82, 1300 - 135 * 0.82, 0.42)
    draw_person(cr, "grandpa", 540 - 330 * 0.82, 1300 - 135 * 0.82 - 5, 22, legs=("sit", 1.8), smile=0.8, blink=blink(t, 2))
    draw_person(cr, "grandma", 540, 1300 - 135 * 0.82, 21, smile=0.8, blink=blink(t, 1))


def sh_s1_run(cr, t, shot):
    dur = shot["frames"] / FPS
    c = cue(shot, "s1_child")
    z, cx, cy = cam_lerp(t, dur, (1.0, 540, 960), (1.08, 540, 980))
    camera(cr, z, cx, cy)
    def bg(c_):
        S.sky(c_, "gold", -900, 1000, -540, 1620, sun=(880, 520, 38, "#ffcf7a"))
        S.clouds(c_, 260, 0, seed=5)
        S.treeline(c_, 1000, -540, 1620, c="#5d7a48", seed=6)
    paint_cached(cr, cached("run_far", bg, blur=4))
    # ground + path in perspective + compound wall & gate behind the boy
    lin(cr, 0, 1000, 0, 2000, [(0, "#6f9a3e"), (1, "#3f6a26")]); cr.rectangle(-540, 1000, 2160, 1100); cr.fill()
    lin(cr, 0, 1000, 0, 2000, [(0, "#b8683c"), (1, "#8f4b2b")])
    cr.move_to(500, 1000); cr.line_to(580, 1000); cr.line_to(980, 2000); cr.line_to(100, 2000); cr.close_path(); cr.fill()
    for xa, xb in ((-540, 470), (610, 1620)):
        col(cr, "#9a4a2b"); cr.rectangle(xa, 960, xb - xa, 60); cr.fill(); col(cr, "#efe3c8"); cr.rectangle(xa, 952, xb - xa, 10); cr.fill()
    for gx in (470, 610):
        col(cr, "#8a4226"); cr.rectangle(gx - 18, 900, 36, 120); cr.fill(); col(cr, "#efe3c8"); cr.rectangle(gx - 22, 892, 44, 10); cr.fill()
    S.palm(cr, 170, 1080, 650, 0.1, 0.05 * math.sin(t)); S.palm(cr, 940, 1060, 620, -0.08, 0.05 * math.sin(t + 2))
    S.banana(cr, 60, 1250, 220, sway=0.1 * math.sin(t)); S.banana(cr, 1040, 1300, 240, sway=0.1 * math.sin(t + 1))
    S.grass_tufts(cr, -100, 1180, 1420, 60, seed=3, h=40)
    # the boy runs toward us
    u = t / dur
    gy = lerp(1110, 1500, u - 0.15 * ss((t - dur + 1.2) / 1.2) * u)
    R = lerp(24, 70, (gy - 1110) / 390)
    back = ss((t - c["start"] + 0.2) / 0.35) * (1 - ss((t - c["start"] - 1.55) / 0.4))
    ph = t * 2 * math.pi * 2.3
    m = mouth(shot, "child", t)
    rig = draw_person(cr, "child", 540 + 10 * math.sin(t * 1.5), gy, R, legs=("walk", ph, 0.5), bob=0.12 * abs(math.sin(ph)),
                      armL=(25 + 30 * math.sin(ph), 40), armR=(25 - 30 * math.sin(ph), 40) if back < 0.3 else (60, 130),
                      turn=0.75 * back, tilt=-0.15 * back, mouth=m, smile=0.9, brows=0.6, blink=blink(t, 3))
    S.grass_tufts(cr, -100, 1180, 1990, 40, seed=4, h=70, c="#3d6a22")


def veranda_bg(c_, aged=0.0, light="gold"):
    """close view of the veranda wall: window, wall, red floor"""
    wall = mix("#f1e6cc", "#b8aa8c", aged)
    lin(c_, -540, 0, 1620, 0, [(0, shade(wall, -0.2)), (0.5, wall), (1, shade(wall, -0.25))]); c_.rectangle(-540, -900, 2160, 2350); c_.fill()
    col(c_, "#5b351f"); rrect(c_, 620, 420, 420, 420, 10); c_.fill()
    lin(c_, 0, 450, 0, 810, [(0, "#2c3d5a"), (1, "#1b2436")]); c_.rectangle(650, 450, 360, 360); c_.fill()
    col(c_, "#7a4a2a")
    for k in range(7):
        c_.rectangle(665 + k * 52, 450, 14, 360); c_.fill()
    lin(c_, 0, -100, 0, 260, [(0, (0, 0, 0, 0.45)), (1, (0, 0, 0, 0))]); c_.rectangle(-540, -900, 2160, 1160); c_.fill()
    lin(c_, 0, 1450, 0, 2900, [(0, "#9a2c1d"), (1, "#5a160c")]); c_.rectangle(-540, 1450, 2160, 1500); c_.fill()
    lin(c_, 0, 1450, 0, 1650, [(0, (1, 0.85, 0.6, 0.25)), (1, (1, 0.85, 0.6, 0))]); c_.rectangle(-540, 1450, 2160, 200); c_.fill()
    col(c_, "#5b351f"); c_.rectangle(-60, -900, 70, 2350); c_.fill()
    lin(c_, -60, 0, 10, 0, [(0, (1, 1, 1, 0.15)), (1, (0, 0, 0, 0.2))]); c_.rectangle(-60, -900, 70, 2350); c_.fill()
    if light == "gold":
        lin(c_, 1080, 200, 300, 1600, [(0, (1, 0.8, 0.45, 0.35)), (1, (1, 0.8, 0.45, 0))]); c_.rectangle(-540, -900, 2160, 3800); c_.fill()


def sh_s1_gma(cr, t, shot):
    c = cue(shot, "s1_gma")
    z, cx, cy = cam_lerp(t, 3.8, (1.0, 540, 960), (1.1, 540, 900))
    camera(cr, z, cx, cy)
    def bg(c_):
        far_day(c_)
        S.house(c_, 540, 2109, 3.4, door_open=True, glow_door=True)
    paint_cached(cr, cached("gma_bg", bg, blur=5))
    open_ = ss((t - c["start"] - 1.0) / 0.7)
    draw_person(cr, "grandma", 540, 1650, 96, mouth=mouth(shot, "grandma", t), smile=0.95, brows=0.5,
                armL=(10 + 65 * open_, 15 + 25 * open_), armR=(10 + 65 * open_, 15 + 25 * open_),
                tilt=0.06 * math.sin(t * 1.3), blink=blink(t, 4), gaze=(0.1, 0.25))


def sh_s1_gpa(cr, t, shot):
    z, cx, cy = cam_lerp(t, 5.6, (1.0, 540, 960), (1.12, 540, 920))
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("ver_bg", lambda c_: veranda_bg(c_), blur=4))
    fw = ss((t - 0.1) / 1.2)
    S.chaarukasera(cr, 560, 1640, 1.9)
    m = mouth(shot, "grandpa", t)
    draw_person(cr, "grandpa", 560, 1600 - 30 * fw, 90, legs=("sit", 2.2), mouth=m, smile=0.9, brows=0.4 * fw,
                armL=(40, 70), armR=(40, 70), turn=-0.15, tilt=-0.05 + 0.06 * math.sin(t * 1.7) * fw,
                blink=blink(t, 5), gaze=(-0.2, 0.2))


def sh_s1_hug(cr, t, shot):
    z, cx, cy = cam_lerp(t, 3.6, (1.0, 540, 1080), (1.12, 560, 1050))
    camera(cr, z, cx, cy)
    def hugbg(c_):
        far_day(c_)
        S.house(c_, 540, 1650, 1.35, door_open=True)
        lin(c_, 0, 1650, 0, 2900, [(0, "#d6b487"), (1, "#b48858")]); c_.rectangle(-540, 1650, 2160, 1300); c_.fill()
    paint_cached(cr, cached("hug_bg", hugbg, blur=0))
    floor = 1650 - 135 * 1.35
    S.chaarukasera(cr, 540 - 330 * 1.35, floor + 30, 0.75)
    laugh = ss((t - 1.0) / 0.5)
    draw_person(cr, "grandpa", 540 - 330 * 1.35, floor + 15, 36, legs=("sit", 2.0), smile=1.0, happy_eyes=laugh > 0.5, blink=laugh,
                mouth=0.35 * laugh * (0.5 + 0.5 * math.sin(t * 10)), armL=(40, 70 + 20 * laugh * math.sin(t * 8)), armR=(40, 70), turn=0.4)
    hug = ss((t - 1.5) / 0.45)
    bend = ss((t - 1.1) / 0.6)
    gx, gy = 560, floor + 10
    draw_person(cr, "grandma", gx, gy, 40, smile=1.0, happy_eyes=hug > 0.5, blink=hug, tilt=0.12 * bend,
                armL=(30 + 20 * (1 - hug) - 40 * hug, 40 + 60 * hug), armR=(30 + 20 * (1 - hug) - 40 * hug, 40 + 60 * hug), lean=0.1 * bend)
    # the boy runs up the steps into her arms (seen from behind)
    u = ss(t / 1.65)
    cxp = lerp(820, gx + 5, u); cyp = lerp(1900, gy + 60, u)
    R = lerp(46, 37, u)
    ph = t * 2 * math.pi * 2.3
    draw_person(cr, "child", cxp, cyp, R, back=True, legs=("walk", ph, 0.4 * (1 - hug)) if hug < 1 else "stand",
                armL=(30 + 120 * hug, 30), armR=(30 + 120 * hug, 30), bob=0.08 * abs(math.sin(ph)) * (1 - hug))


def sh_kitchen(cr, t, shot, zoom=(1.0, 540, 960), zoom2=None, feed=0.0, dur=5.0, chew=False):
    z, cx, cy = cam_lerp(t, dur, zoom, zoom2 or zoom)
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("kit_bg", lambda c_: S.kitchen(c_, 0), blur=2))
    S.kitchen_fire(cr, t)
    # stools
    for (sx_, w_) in ((300, 230), (790, 190)):
        col(cr, "#6e4126"); rrect(cr, sx_ - w_ / 2, 1505, w_, 32, 8); cr.fill()
        col(cr, "#4e2c18"); cr.rectangle(sx_ - w_ / 2 + 15, 1535, 18, 90); cr.fill(); cr.rectangle(sx_ + w_ / 2 - 33, 1535, 18, 90); cr.fill()
    gR, cR = 86, 84
    m_g = mouth(shot, "grandma", t); m_c = mouth(shot, "child", t)
    # child first (so grandma's feeding arm overlaps)
    crig = draw_person(cr, "child", 790, 1620, cR, legs=("sit", 1.35), turn=-0.45, smile=1.0, brows=0.4,
                       mouth=m_c if not chew else 0.0, armL=(25, 70), armR=(25, 70), blink=blink(t, 6), gaze=(-0.6, 0.0))
    if chew:
        crig = None
    grig = draw_person(cr, "grandma", 300, 1620, gR, legs=("sit", 1.35), turn=0.45, smile=0.9, mouth=m_g, gaze=(0.6, 0.1),
                       armR=(15, 80), armL=(20, 60), blink=blink(t, 7))
    # plate on her lap
    px, py = 330, 1440
    shadow(cr, px, py + 18, 120, 20, 0.3)
    lin(cr, px - 120, 0, px + 120, 0, [(0, "#9aa3a8"), (0.5, "#f4f6f7"), (1, "#8a9398")]); ellipse(cr, px, py, 120, 34); cr.fill()
    col(cr, "#fbf6ea"); ellipse(cr, px + 10, py - 6, 60, 18); cr.fill()
    col(cr, "#d27a24"); ellipse(cr, px - 60, py - 2, 26, 9); cr.fill()
    col(cr, "#9ab83a"); ellipse(cr, px + 70, py, 24, 8); cr.fill()
    return grig


def feeding_arm(cr, grig, target, t):
    """grandma's screen-right arm reaching to a target (drawn on top)"""
    R = grig.R
    shx, shy = grig.shoulder[1]
    tx, ty = target
    a = chars.ik(1, shx / R, shy / R, tx / R, ty / R, 1.25, 1.15, True)
    p0, p1, p2 = chars.arm_points(1, shx, shy, a[0], a[1], 1.25 * R, 1.15 * R)
    skin = chars.SPEC["grandma"]["skin"]
    from draw import limb
    limb(cr, [p0, p1, p2], 0.26 * R * 1.25, shade(skin, -0.1), 0.26 * R * 1.05)
    limb(cr, [p0, (p0[0] + (p1[0] - p0[0]) * 0.4, p0[1] + (p1[1] - p0[1]) * 0.4)], 0.26 * R * 1.75, "#8a2131")
    col(cr, skin); cr.arc(p2[0], p2[1], 0.26 * R * 0.78, 0, 6.3); cr.fill()
    col(cr, "#fbf6ea"); cr.arc(p2[0] + 8, p2[1] - 10, 0.26 * R * 0.35, 0, 6.3); cr.fill()   # rice ball
    col(cr, "#d6a53a"); cr.set_line_width(5); ellipse(cr, p2[0] - (p2[0] - p1[0]) * 0.2, p2[1] - (p2[1] - p1[1]) * 0.2, 16, 7, math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + 1.57); cr.stroke()


def sh_s2_wide(cr, t, shot):
    grig = sh_kitchen(cr, t, shot, (1.0, 540, 1120), (1.08, 540, 1150), dur=4.8)
    feeding_arm(cr, grig, (330 + 40 * math.cos(t * 4), 1420 + 12 * math.sin(t * 4)), t)


def sh_s2_child(cr, t, shot):
    c = cue(shot, "s2_child")
    feed = ss(t / 0.6) * (1 - ss((t - 1.1) / 0.5))
    chewing = 1.0 < t < c["start"]
    grig = sh_kitchen(cr, t, shot, (1.75, 690, 1240), (1.85, 700, 1250), dur=5.4)
    # re-draw the boy's mouth state handled via mouth(); add chew/open overlay by drawing him again on top
    m = 0.85 if 0.4 < t < 0.95 else (0.12 * abs(math.sin(t * 11)) if chewing else mouth(shot, "child", t))
    happy = ss((t - 1.0) / 0.3) * (1 - ss((t - c["start"]) / 0.3))
    draw_person(cr, "child", 790, 1620, 84, legs=("sit", 1.35), turn=-0.45, smile=1.0, brows=0.5, mouth=m,
                armL=(25, 70), armR=(25, 70), happy_eyes=happy > 0.5, blink=happy if happy > 0.5 else blink(t, 6), gaze=(-0.6, 0))
    mouth_pt = (790 - 0.45 * 0.3 * 84 - 0.05 * 84, 1620 - (1.35 + 1.55 + 0.12 + 0.95 - 0.6) * 84)
    rest = (330, 1420)
    tgt = (lerp(rest[0], mouth_pt[0] - 25, feed), lerp(rest[1], mouth_pt[1] + 10, feed))
    feeding_arm(cr, grig, tgt, t)


def sh_s2_gma(cr, t, shot):
    grig = sh_kitchen(cr, t, shot, (1.75, 370, 1170), (1.85, 360, 1170), dur=3.6)
    feeding_arm(cr, grig, (330 + 40 * math.cos(t * 4), 1420 + 12 * math.sin(t * 4)), t)


def lane_bg(c_):
    S.sky(c_, "gold", -900, 980, -540, 1620, sun=(300, 500, 36, "#ffcf7a"))
    S.clouds(c_, 220, 0, seed=8)
    S.treeline(c_, 980, -540, 1620, c="#57774a", seed=9)


def lane_ground(cr, t, scroll=0.0):
    lin(cr, 0, 980, 0, 2000, [(0, "#79a743"), (1, "#4d7d2a")]); cr.rectangle(-540, 980, 2160, 1100); cr.fill()
    # paddy rows on the right with water glints
    col(cr, "#5a8a2e"); cr.set_line_width(3)
    for k in range(18):
        y = 990 + (k ** 1.6) * 9 + (scroll * 0.5 % 1) * 0
        col(cr, (0.35, 0.55, 0.2, 0.6)); cr.move_to(600, y); cr.line_to(1620, y + 40); cr.stroke()
    lin(cr, 0, 980, 0, 2000, [(0, "#c07a4a"), (1, "#94532f")])
    cr.move_to(500, 980); cr.line_to(560, 980); cr.line_to(900, 2000); cr.line_to(140, 2000); cr.close_path(); cr.fill()
    col(cr, (0, 0, 0, 0.08)); cr.set_line_width(3)
    for k in range(14):
        v = ((k + scroll * 2) % 14) / 14
        y = 980 + 1020 * v ** 2
        w = lerp(30, 380, v ** 2)
        cr.move_to(530 - w, y); cr.line_to(530 + w, y); cr.stroke()
    S.grass_tufts(cr, 600, 1620, 1100, 60, c="#6a9a32", h=36, seed=11)
    S.grass_tufts(cr, -540, 480, 1100, 40, c="#4e7d2a", h=36, seed=12)


def walkers(cr, t, shot, gy, Rg, Rc, talk_look=0.0, scale_x=1.0):
    ph = t * 2 * math.pi * 0.9
    cx_, gx_ = 540 - 75 * scale_x * Rg / 60, 540 + 70 * scale_x * Rg / 60
    m_c, m_g = mouth(shot, "child", t), mouth(shot, "grandpa", t)
    look_c = 1.0 if shot["cues"] and any(c["speaker"] == "child" and c["start"] - 0.3 < t < c["start"] + c["dur"] + 0.2 for c in shot["cues"]) else 0.3
    look_g = 1.0 if any(c["speaker"] == "grandpa" and c["start"] - 0.3 < t < c["start"] + c["dur"] + 0.2 for c in shot["cues"]) else 0.5
    # hands meet between them
    hand = ((cx_ + gx_) / 2, gy - 2.25 * Rg)
    rg = draw_person(cr, "grandpa", gx_, gy, Rg, legs=("walk", ph * 0.75), armR={"target": (hand[0] - gx_, hand[1] - gy), "up": False},
                     armL=(8 - 10 * math.sin(ph * 0.75), 15), turn=-0.35 * look_g, tilt=-0.08 * look_g, mouth=m_g, smile=0.85,
                     gaze=(-0.5 * look_g, 0.3 * look_g), blink=blink(t, 8))
    rc = draw_person(cr, "child", cx_, gy + 4, Rc, legs=("walk", ph * 1.3, 0.3), armL={"target": (hand[0] - cx_, hand[1] - gy - 4), "up": False},
                     armR=(10 + 15 * math.sin(ph * 1.3), 20), turn=0.45 * look_c, tilt=0.1 * look_c, mouth=m_c, smile=0.95, brows=0.5,
                     gaze=(0.5 * look_c, -0.6 * look_c), blink=blink(t, 9), bob=0.05 * abs(math.sin(ph * 1.3)))


def sh_s3_walk(cr, t, shot):
    dur = shot["frames"] / FPS
    z, cx, cy = cam_lerp(t, dur, (1.0, 540, 980), (1.12, 540, 1100))
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("lane_far", lane_bg, blur=4))
    lane_ground(cr, t, scroll=t * 0.25)
    for (x, y, h, l) in ((40, 1150, 760, 0.1), (230, 1040, 520, 0.05), (-120, 1500, 1000, 0.08), (1060, 1120, 700, -0.1)):
        S.palm(cr, x, y, h, l, 0.05 * math.sin(t + x))
    u = t / dur
    gy = lerp(1380, 1560, u)
    walkers(cr, t, shot, gy, lerp(48, 60, u), lerp(52, 64, u))
    S.grass_tufts(cr, -540, 1620, 1990, 50, c="#3d6a22", h=80, seed=13)


def sh_s3_two(cr, t, shot):
    camera(cr, 1.75, 540, 1330 - 8 * t)
    paint_cached(cr, cached("lane_far", lane_bg, blur=4))
    lane_ground(cr, t + 8, scroll=(t + 8) * 0.25)
    S.palm(cr, 120, 1100, 720, 0.1, 0.05 * math.sin(t))
    moved = ss((t - 2.6) / 0.6)
    walkers(cr, t, shot, 1660, 62, 66)


def sh_s3_shop(cr, t, shot):
    z, cx, cy = cam_lerp(t, 3.8, (1.0, 540, 1100), (1.1, 480, 1150))
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("lane_far", lane_bg, blur=4))
    lane_ground(cr, 0)
    S.palm(cr, 1000, 1150, 720, -0.1, 0.05 * math.sin(t))
    S.petti_kada(cr, 300, 1450, 1.05)
    u = ss(t / 1.8)
    hop = max(0, math.sin((t - 2.3) * 8)) * (1 if 2.3 < t < 3.3 else 0)
    ph = t * 2 * math.pi * 0.9 * (1 - u)
    draw_person(cr, "grandpa", lerp(800, 690, u), lerp(1700, 1560, u), 56, legs=("walk", ph) if u < 0.98 else "stand",
                turn=-0.5, armR=(55, 30) if t > 2 else (8, 15), smile=0.9, blink=blink(t, 10), gaze=(-0.8, 0))
    draw_person(cr, "child", lerp(620, 540, u), lerp(1730, 1600 - 50 * hop, u), 60, legs=("walk", ph * 1.4, 0.3) if u < 0.98 else "stand",
                turn=-0.6, armR=(150 * ss((t - 2.2) / 0.3), 20), smile=1.0, brows=0.8, mouth=0.3 * ss((t - 2.2) / 0.3), gaze=(-0.9, -0.3),
                blink=blink(t, 11))


def bed_set(cr, t, night=True):
    paint_cached(cr, cached("bed_bg_n" if night else "bed_bg_d", lambda c_: S.bedroom(c_, night, 0), blur=2))
    S.cot(cr, 540, 1480, 760)


def bed_scene(cr, t, shot, z0, z1, dur, gma_kw=None, child_kw=None, stroke=0.0):
    z, cx, cy = cam_lerp(t, dur, z0, z1)
    camera(cr, z, cx, cy)
    bed_set(cr, t)
    # lamp on a stool at the left
    col(cr, "#4e2c18"); rrect(cr, 30, 1360, 190, 30, 6); cr.fill(); cr.rectangle(55, 1390, 20, 200); cr.fill(); cr.rectangle(175, 1390, 20, 200); cr.fill()
    S.nilavilakku(cr, 125, 1362, 0.9, t)
    ck = dict(smile=0.8, blink=blink(t, 12), gaze=(0.5, -0.2), turn=0.25, tilt=0.12)
    ck.update(child_kw or {})
    chars.draw_head_at(cr, "child", 540, 1215, 78, **ck)
    draw_blanket(cr, 540, 1290, 78, 4.6, 2.3)
    gk = dict(legs=("sit", 2.0), turn=-0.55, smile=0.85, gaze=(-0.7, 0.3), tilt=-0.08, blink=blink(t, 13), armR=(15, 70), armL=(15, 80))
    gk.update(gma_kw or {})
    grig = draw_person(cr, "grandma", 770, 1660, 80, **gk)
    # warm lamp light over everything
    glow(cr, 125, 1150, 900, "#ff9a3a", 0.1 * (1 + 0.08 * math.sin(t * 13)))
    return grig


def sh_s4_wide(cr, t, shot):
    bed_scene(cr, t, shot, (1.0, 540, 1050), (1.08, 560, 1080), 5.4, child_kw=dict(mouth=mouth(shot, "child", t), brows=0.6),
              gma_kw=dict(mouth=0))


def sh_s4_story(cr, t, shot):
    g = 0.5 + 0.5 * math.sin(t * 2.2)
    bed_scene(cr, t, shot, (1.9, 760, 1200), (2.0, 760, 1190), 3.8, gma_kw=dict(mouth=mouth(shot, "grandma", t), brows=0.7, armR=(60 + 25 * g, 110)))


def sh_s4_eager(cr, t, shot):
    lift = ss(t / 0.3)
    bed_scene(cr, t, shot, (2.2, 560, 1180), (2.3, 560, 1180), 2.2, child_kw=dict(mouth=mouth(shot, "child", t), brows=1.0, gaze=(0.6, -0.3), tilt=0.05 + 0.05 * lift))


def sh_s4_sleep(cr, t, shot):
    dur = shot["frames"] / FPS
    c = cue(shot, "s4_gma2")
    sleepy = ss((t - c["start"] - 1.5) / 2.5)
    u = ss((t - (dur - 2.8)) / 2.6)
    z0 = (1.3, 640, 1150); z1 = (3.2, 85, 1150)
    stroke = math.sin(t * 2.0)
    grig = bed_scene(cr, t, shot, z0, z0, dur, child_kw=dict(sleepy=sleepy, blink=0 if sleepy > 0.5 else blink(t, 12), smile=0.7),
                     gma_kw=dict(mouth=mouth(shot, "grandma", t), armR={"target": (540 - 870 + 40 + 25 * stroke, 1150 - 1660), "up": True}))
    if u > 0:
        # drift to the lamp flame
        cr.identity_matrix()
        col(cr, (0, 0, 0, 0)); cr.paint()


def sh_s4_sleep_wrap(cr, t, shot):
    dur = shot["frames"] / FPS
    u = ss((t - (dur - 2.8)) / 2.6)
    z = lerp(1.3, 3.0, u); cx = lerp(640, 100, u); cy = lerp(1150, 1170, u)
    c = cue(shot, "s4_gma2")
    sleepy = ss((t - c["start"] - 1.5) / 2.5)
    stroke = math.sin(t * 2.0)
    bed_scene(cr, t, shot, (z, cx, cy), (z, cx, cy), dur, child_kw=dict(sleepy=sleepy, blink=0 if sleepy > 0.5 else blink(t, 12), smile=0.7),
              gma_kw=dict(mouth=mouth(shot, "grandma", t), armR={"target": (560 - 770 + 25 * stroke, 1180 - 1660), "up": True}))


def ext_house(cr, t, aged, sky_kind, z, cx, cy, chair=True, extra=None, sun=None, sway=1.0, figures=0.0):
    camera(cr, z, cx, cy)
    S.sky(cr, sky_kind, -900, 1060, -540, 1620, t=t, sun=sun)
    S.clouds(cr, 250, t, c="#ffe8d0" if sky_kind != "night" else "#3a4a6a", a=0.4)
    S.treeline(cr, 1060, -540, 1620, c=mix("#5d7a48", "#3a4a44", 0.5 if sky_kind in ("dusk", "night") else 0), seed=4)
    yard(cr, aged=aged)
    if chair:
        S.chaarukasera(cr, 540 - 330 * 0.82, 1300 - 135 * 0.82 + 3, 0.42, rock=0.03 * math.sin(t * 1.8))
    if figures > 0:
        fl = 1300 - 135 * 0.82
        draw_person(cr, "grandpa", 540 - 330 * 0.82, fl - 5, 22, legs=("sit", 1.8), smile=0.9, alpha=figures)
        draw_person(cr, "grandma", 540 - 40, fl, 21, smile=0.9, alpha=figures)
        draw_person(cr, "child", 540 + 30, fl, 20, smile=1.0, alpha=figures, armR=(40, 30))
    S.palm(cr, -40, 1500, 900, 0.12, 0.05 * sway * math.sin(t * 1.2)); S.palm(cr, 1120, 1520, 950, -0.1, 0.05 * sway * math.sin(t * 1.1 + 1))
    if sky_kind in ("dusk", "night"):
        col(cr, (0.15, 0.1, 0.25, 0.25 if sky_kind == "dusk" else 0.5)); cr.rectangle(-540, -900, 2160, 3800); cr.fill()


def sh_s5_timelapse(cr, t, shot):
    u = t / 5.5
    cyc = (u * 3.0) % 1.0
    day = math.sin(math.pi * cyc)
    kind = [(0, mix("#1a2a50", "#8cbfd8", day)), (0.6, mix("#24365a", "#e9cfa0", day)), (1, mix("#2a3a5a", "#f7c27a", day))]
    z, cx, cy = cam_lerp(t, 5.5, (1.0, 540, 900), (1.25, 500, 1000))
    ext_house(cr, t * 4, ss(u), kind, z, cx, cy, sun=(lerp(-200, 1300, cyc), 900 - 600 * day, 36, "#ffd08a") if day > 0.15 else None, sway=3)
    col(cr, (0.05, 0.06, 0.15, 0.55 * (1 - day))); cr.identity_matrix(); cr.rectangle(0, 0, W, H); cr.fill()


def sh_s5_return(cr, t, shot):
    z, cx, cy = cam_lerp(t, 5.0, (1.0, 540, 960), (1.1, 540, 1000))
    ext_house(cr, t, 1.0, "dusk", z, cx, cy, sun=(900, 950, 34, "#ff9a5a"))
    walk_t = min(t, 3.4)
    slow = ss((t - 2.4) / 1.0)
    gy = lerp(2050, 1560, ss(walk_t / 3.6))
    R = lerp(78, 50, ss(walk_t / 3.6))
    ph = t * 2 * math.pi * 0.85 * (1 - slow)
    draw_person(cr, "adult", 600, gy, R, back=True, legs=("walk", ph) if slow < 0.95 else "stand",
                armL=(6 + 10 * math.sin(ph) * (1 - slow), 10), armR=(6 - 10 * math.sin(ph) * (1 - slow), 10))


def photo_surface():
    """the old family photograph (drawn with the same characters)"""
    if "photo" in _cache:
        return _cache["photo"]
    s, cr = new_surface(900, 680)
    cr.translate(450, 0); cr.scale(0.62, 0.62); cr.translate(-540, -600)
    S.sky(cr, "day", -900, 1060, -540, 1620)
    S.house(cr, 540, 1650, 1.25, door_open=True)
    lin(cr, 0, 1480, 0, 1800, [(0, "#d6b487"), (1, "#b48858")]); cr.rectangle(-540, 1480, 2160, 400); cr.fill()
    draw_person(cr, "grandma", 380, 1560, 52, smile=1.0, armL=(-20, 30))
    draw_person(cr, "grandpa", 700, 1560, 52, smile=1.0, armR=(-20, 30))
    draw_person(cr, "child", 540, 1600, 56, smile=1.0, mouth=0.4, armL=(40, 20), armR=(40, 20))
    _cache["photo"] = s
    return s


def sh_s5_face(cr, t, shot):
    z, cx, cy = cam_lerp(t, 4.2, (1.75, 540, 1330), (1.85, 540, 1340))
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("bed_bg_d", lambda c_: S.bedroom(c_, False, 0), blur=2))
    col(cr, (0.3, 0.25, 0.2, 0.15)); cr.rectangle(-540, -900, 2160, 3800); cr.fill()
    px, py = 540, 1540
    draw_person(cr, "adult", 540, 1800, 70, smile=0.3 + 0.2 * ss((t - 2.5) / 1.0), gaze=(0, 0.9), sleepy=0.35, tilt=0.05,
                armL={"target": (px + 95 - 540, py + 40 - 1800), "up": False}, armR={"target": (px - 95 - 540, py + 40 - 1800), "up": False})
    S.photo_frame(cr, px, py, 170, 128, photo_surface(), sepia=0.3)
    sk = chars.SPEC["adult"]["skin"]
    for sx in (-1, 1):
        col(cr, sk); ellipse(cr, px + sx * 98, py + 30, 20, 28); cr.fill()


def sh_s5_photo(cr, t, shot):
    dur = shot["frames"] / FPS
    z = lerp(1.0, 1.25, ss(t / dur))
    camera(cr, z, 540, 900)
    lin(cr, 0, 0, 0, 1920, [(0, "#5a4636"), (1, "#2a1e16")]); cr.rectangle(-540, -900, 2160, 3800); cr.fill()
    glow(cr, 900, 300, 900, "#ffc27a", 0.35)
    S.photo_frame(cr, 540, 880, 780, 590, photo_surface(), sepia=0.32)
    sk = chars.SPEC["adult"]["skin"]
    for sx in (-1, 1):   # his hands holding the frame
        col(cr, shade(sk, -0.1)); ellipse(cr, 540 + sx * 420, 1100, 60, 80, sx * 0.4); cr.fill()
        col(cr, sk); ellipse(cr, 540 + sx * 395, 1060, 26, 52, sx * 0.3); cr.fill()
        col(cr, "#eaa92c"); cr.rectangle(540 + sx * 440 - 70, 1160, 140, 800); cr.fill()


def sh_s6_veranda(cr, t, shot):
    z, cx, cy = cam_lerp(t, 5.3, (1.0, 540, 980), (1.12, 560, 1000))
    camera(cr, z, cx, cy)
    paint_cached(cr, cached("ver_bg_aged", lambda c_: veranda_bg(c_, aged=0.8, light="gold"), blur=3))
    S.chaarukasera(cr, 560, 1640, 1.9, rock=0.025 * math.sin(t * 1.7))
    rnd = random.Random(3)
    for k in range(9):   # dry leaves on the floor
        col(cr, ["#a5722a", "#8a5a22", "#c08a3a"][k % 3]); ellipse(cr, rnd.uniform(80, 1000), rnd.uniform(1700, 1880), 22, 9, rnd.uniform(0, 3)); cr.fill()
    col(cr, (0.2, 0.12, 0.25, 0.18)); cr.rectangle(-540, -900, 2160, 3800); cr.fill()


def sh_s6_toys(cr, t, shot):
    z, cx, cy = cam_lerp(t, 5.8, (1.6, 540, 1450), (1.75, 600, 1460))
    camera(cr, z, cx, cy)
    bed_set(cr, t, night=False)
    col(cr, (0.3, 0.25, 0.2, 0.18)); cr.rectangle(-540, -900, 2160, 3800); cr.fill()
    S.toys(cr, 520, 1700, 1.0)


def sh_s6_photo(cr, t, shot):
    z, cx, cy = cam_lerp(t, 5.2, (1.0, 540, 900), (1.25, 540, 880))
    camera(cr, z, cx, cy)
    wall = "#c9b593"
    lin(cr, 0, 0, 0, 1920, [(0, shade(wall, -0.3)), (1, wall)]); cr.rectangle(-540, -900, 2160, 3800); cr.fill()
    lin(cr, 1080, 0, 0, 1500, [(0, (1, 0.8, 0.45, 0.4)), (1, (1, 0.8, 0.45, 0))]); cr.rectangle(-540, -900, 2160, 3800); cr.fill()
    S.photo_frame(cr, 540, 860, 560, 420, photo_surface(), sepia=0.4, garland=True)
    col(cr, "#5b351f"); cr.rectangle(200, 1250, 680, 26); cr.fill()
    S.nilavilakku(cr, 540, 1250, 0.55, t, lit=True)


def sh_s6_final(cr, t, shot):
    dur = shot["frames"] / FPS
    z, cx, cy = cam_lerp(t, dur, (1.35, 520, 1100), (0.95, 540, 950))
    c = cue(shot, "s6_final")
    fig = 0.4 * ss((t - c["start"] - 1.0) / 1.5) * (1 - ss((t - c["start"] - c["dur"]) / 1.5))
    ext_house(cr, t, 0.7, "dusk", z, cx, cy, sun=(860, 980, 34, "#ff9a5a"), figures=fig)


FUNCS = {"title": sh_title, "s1_run": sh_s1_run, "s1_gma": sh_s1_gma, "s1_gpa": sh_s1_gpa, "s1_hug": sh_s1_hug,
         "s2_wide": sh_s2_wide, "s2_child": sh_s2_child, "s2_gma": sh_s2_gma, "s3_walk": sh_s3_walk, "s3_two": sh_s3_two,
         "s3_shop": sh_s3_shop, "s4_wide": sh_s4_wide, "s4_story": sh_s4_story, "s4_eager": sh_s4_eager, "s4_sleep": sh_s4_sleep_wrap,
         "s5_timelapse": sh_s5_timelapse, "s5_return": sh_s5_return, "s5_face": sh_s5_face, "s5_photo": sh_s5_photo,
         "s6_veranda": sh_s6_veranda, "s6_toys": sh_s6_toys, "s6_photo": sh_s6_photo, "s6_final": sh_s6_final}


def frame(name, f):
    return render(FUNCS, name, f)
