"""Shot list + per-frame animation. Each shot: build(ctx) -> anim(f, t)."""
import math, json, os
import bpy
from mathutils import Vector, Quaternion
import lib, sets, render_setup as R
from lib import d

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30

from timeline import SHOTS, timeline  # noqa: E402  (shared with the 2D pipeline)


# --------------------------------------------------------------- helpers
def ss(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


class Ctx:
    def __init__(self, shot, meta):
        self.shot = shot; self.meta = meta; self.chars = {}

    def mouth(self, who, t):
        """mouth openness for character at shot time t"""
        for c in self.shot["cues"]:
            if c["speaker"] == who and c["start"] <= t < c["start"] + c["dur"]:
                env = self.meta[c["id"]]["env"]
                k = int((t - c["start"]) * FPS)
                if 0 <= k < len(env):
                    v = env[k]
                    # vary shape a little so it reads as speech, not a flapping jaw
                    return min(1.0, v * (0.75 + 0.25 * math.sin(t * 23.0)))
        return 0.0

    def speaking(self, who, t, pad=0.0):
        return any(c["speaker"] == who and c["start"] - pad <= t < c["start"] + c["dur"] + pad for c in self.shot["cues"])

    def cue(self, lid):
        for c in self.shot["cues"]:
            if c["id"] == lid:
                return c


def reach(P, i, target, bend=15):
    """two-bone IK: put the wrist of arm i (0=L,1=R) on the world target (elbow bends down/back)"""
    bpy.context.view_layer.update()
    sh = P.sh[i]
    pm = sh.parent.matrix_world
    shw = pm @ sh.location
    vv = pm.to_3x3().inverted() @ (Vector(target) - shw)
    a1, a2 = P.a1, P.a2
    D = max(abs(a1 - a2) + 0.01, min(a1 + a2 - 0.005, vv.length))
    v = vv.normalized()
    ce = (a1 * a1 + a2 * a2 - D * D) / (2 * a1 * a2)
    bendang = math.pi - math.acos(max(-1, min(1, ce)))
    ca = (a1 * a1 + D * D - a2 * a2) / (2 * a1 * D)
    alpha = math.acos(max(-1, min(1, ca)))
    q = Vector((0, 0, -1)).rotation_difference(v)
    q = q @ Quaternion((1, 0, 0), alpha)
    sh.rotation_euler = q.to_euler()
    P.el[i].rotation_euler = (-bendang, 0, 0)


def head_look(P, target, amount=1.0, extra=(0, 0), limit=70):
    bpy.context.view_layer.update()
    yaw, pitch = lib.look_angles(P, target)
    yaw = max(-limit, min(limit, yaw)) * amount + extra[0]
    pitch = max(-45, min(45, pitch)) * amount + extra[1]
    # split between neck and head for a natural turn
    P.neck.rotation_euler = (d(-pitch * 0.4), 0, d(yaw * 0.4))
    P.head.rotation_euler = (d(-pitch * 0.6), 0, d(yaw * 0.6))


def gaze_at(P, target):
    bpy.context.view_layer.update()
    hw = P.head.matrix_world
    v = hw.to_3x3().inverted() @ (Vector(target) - hw.translation)
    yaw = math.degrees(math.atan2(v.x, -v.y)); pitch = math.degrees(math.atan2(v.z, math.hypot(v.x, v.y)))
    return (max(-25, min(25, yaw)) * 0.6, max(-20, min(20, pitch)) * 0.6)


def headpos(P):
    bpy.context.view_layer.update()
    return P.head.matrix_world.translation.copy()


def breathe(P, t, amt=1.0):
    P.chest.rotation_euler.x += d(1.2 * amt * math.sin(t * 1.6))
    P.head.rotation_euler.z += d(1.0 * amt * math.sin(t * 0.7))


# --------------------------------------------------------------- lighting rigs
def light_golden(elev=14, azim=235, energy=5.0, sky=0.38, color=(1.0, 0.68, 0.40)):
    R.sky_world(elev, azim - 90, sky)
    R.sun(elev=elev, azim=azim, energy=energy, color=color, angle=4)


def light_dusk():
    R.sky_world(3, 250 - 90, 0.35, tint=(1.0, 0.75, 0.8, 1), dust=3.0)
    R.sun(elev=5, azim=250, energy=2.6, color=(1.0, 0.55, 0.38), angle=5)


# --------------------------------------------------------------- shots
def make_chars(ctx, keys):
    for k in keys:
        P = lib.make_person(k)
        lib.stand(P)
        ctx.chars[k] = P
    return [ctx.chars[k] for k in keys]


def build_title(ctx, aged=False, timelapse=False, dusk=False, final=False):
    mats = sets.M()
    H, palms = sets.exterior(mats)
    chair = sets.chaarukasera("chair", H["chair"], 8, mats)
    if dusk or final:
        light_dusk()
    else:
        light_golden()
    cam = R.camera(lens=28, fstop=5.6)
    ctx.H, ctx.palms, ctx.chair, ctx.mats, ctx.cam = H, palms, chair, mats, cam
    return mats


def shot_title(ctx):
    build_title(ctx)
    cam = ctx.cam
    def anim(f, t):
        u = ss(t / 5.0)
        sets.sway(ctx.palms, t)
        R.aim(cam, lerp((0.0, -27, 10.5), (0.6, -21, 3.2), u), lerp((0, 3, 3.5), (0, 2, 2.4), u))
    return anim


def shot_s1_run(ctx):
    build_title(ctx)
    child, gma, gpa = make_chars(ctx, ["child", "grandma", "grandpa"])
    lib.place(gma, ctx.H["door"], 0)
    lib.place(gpa, ctx.H["chair"] + Vector((0, 0.12, 0)), 8); lib.sit(gpa, 0.30, lean=-14)
    ctx.cam.data.lens = 32; ctx.cam.data.dof.aperture_fstop = 2.8
    dur = ctx.shot["frames"] / FPS
    y0, y1 = -11.0, -2.0
    c = ctx.cue("s1_child")
    def anim(f, t):
        sets.sway(ctx.palms, t)
        u = t / dur
        slow = ss((t - (dur - 1.2)) / 1.2)
        y = y0 + (y1 - y0) * (u - 0.12 * slow * u)
        lib.place(child, (0.15 * math.sin(t * 1.4), y, 0), 180)   # runs toward +Y (the house)
        lib.rest_pose(child)
        lib.walk(child, t, stride=42, arm=45, bob=0.045, speed=2.4 * (1 - 0.5 * slow), knee=65, run=True)
        # calls back to Amma (behind him) then faces the house
        back = ss((t - c["start"] + 0.3) / 0.4) * (1 - ss((t - c["start"] - 1.6) / 0.5))
        head_look(child, Vector((0, 4, 1.6)), 1.0 - back)
        if back > 0.01:
            child.chest.rotation_euler.z = d(-22 * back)
            child.neck.rotation_euler.z = d(-30 * back)
            child.head.rotation_euler.z = d(-35 * back)
            child.sh[1].rotation_euler = (d(-120 * back), d(20), d(30 * back))   # hand cupped to mouth
            child.el[1].rotation_euler = (d(-110 * back), 0, 0)
        lib.face(child, f, mouth=ctx.mouth("child", t), smile=0.9, brows=0.5)
        lib.face(gma, f, smile=0.7); lib.face(gpa, f, smile=0.7)
        hp = headpos(child)
        # camera ahead of the child, low, looking back at him with the gate behind
        R.aim(ctx.cam, (hp.x + 0.5, hp.y + 2.6 - 0.6 * u, 0.85), (hp.x, hp.y, hp.z - 0.12), focus=hp)
    return anim


def shot_s1_gma(ctx):
    build_title(ctx)
    gma, = make_chars(ctx, ["grandma"])
    lib.place(gma, ctx.H["door"] + Vector((0, -0.25, 0)), 0)
    ctx.cam.data.lens = 50; ctx.cam.data.dof.aperture_fstop = 2.0
    c = ctx.cue("s1_gma")
    def anim(f, t):
        sets.sway(ctx.palms, t)
        lib.stand(gma)
        open_ = ss((t - c["start"] - 1.0) / 0.8)
        for i, sx in enumerate((1, -1)):
            gma.sh[i].rotation_euler = (d(-10 - 45 * open_), d(-sx * (8 + 40 * open_)), 0)
            gma.el[i].rotation_euler = (d(-25 - 20 * open_), 0, 0)
        gma.chest.rotation_euler.x = d(6 * open_)
        breathe(gma, t)
        head_look(gma, Vector((0.2, -2.0, 1.0)), 0.8, extra=(0, 0))
        gma.head.rotation_euler.y = d(6 * math.sin(t * 0.8))
        lib.face(gma, f, mouth=ctx.mouth("grandma", t), smile=0.95, brows=0.6 * ss((t - 0.2) / 0.4),
                 gaze=gaze_at(gma, (0.2, -1.5, 1.0)))
        hp = headpos(gma)
        u = ss(t / 3.5)
        R.aim(ctx.cam, (0.45 - 0.15 * u, hp.y - 2.6 + 0.35 * u, hp.z - 0.45), (hp.x, hp.y, hp.z - 0.3), focus=hp)
    return anim


def shot_s1_gpa(ctx):
    build_title(ctx)
    gpa, = make_chars(ctx, ["grandpa"])
    lib.place(gpa, ctx.H["chair"] + Vector((0, 0.12, 0)), 8)
    ctx.cam.data.lens = 50; ctx.cam.data.dof.aperture_fstop = 2.0
    c = ctx.cue("s1_gpa")
    def anim(f, t):
        sets.sway(ctx.palms, t)
        fw = ss((t - 0.1) / 1.2)
        lib.sit(gpa, 0.30, lean=-14 + 24 * fw)
        for i, sx in enumerate((1, -1)):
            gpa.sh[i].rotation_euler = (d(-25), d(-sx * 22), 0)
            gpa.el[i].rotation_euler = (d(-55), 0, 0)
        # playful raised hand on "enthokkeya kalikkendath?"
        wave = ss((t - c["start"] - 1.8) / 0.5)
        gpa.chest.rotation_euler.y = d(3 * math.sin(t * 2.0) * wave)
        target = Vector((-2.2, -1.5, 1.0))
        head_look(gpa, target, 0.9)
        gpa.head.rotation_euler.y = d(-7 * math.sin(t * 1.1))
        lib.face(gpa, f, mouth=ctx.mouth("grandpa", t), smile=0.9, brows=0.5 * fw, gaze=gaze_at(gpa, target))
        hp = headpos(gpa)
        u = ss(t / 5.0)
        R.aim(ctx.cam, (hp.x + 0.75 - 0.2 * u, hp.y - 2.2 + 0.3 * u, hp.z - 0.2), (hp.x, hp.y, hp.z - 0.35), focus=hp)
    return anim


def shot_s1_hug(ctx):
    build_title(ctx)
    child, gma, gpa = make_chars(ctx, ["child", "grandma", "grandpa"])
    door = ctx.H["door"]
    lib.place(gma, door + Vector((0, -0.6, 0)), 0)
    lib.place(gpa, ctx.H["chair"] + Vector((0, 0.12, 0)), 8)
    ctx.cam.data.lens = 30; ctx.cam.data.dof.aperture_fstop = 4
    def anim(f, t):
        sets.sway(ctx.palms, t)
        # child runs up the steps into grandma's arms
        u = ss(t / 1.7)
        y = -1.2 + (door.y - 1.15 + 1.2) * u
        z = 0.45 * ss((y - 0.35) / 0.95)
        lib.place(child, (0.0, y, z), 180)
        lib.rest_pose(child)
        hug = ss((t - 1.5) / 0.5)
        if hug < 1:
            lib.walk(child, t, stride=40 * (1 - hug), arm=40 * (1 - hug), bob=0.04 * (1 - hug), speed=2.4, knee=60, run=True)
        for i, sx in enumerate((1, -1)):
            child.sh[i].rotation_euler = (d(-10 - 140 * hug), d(-sx * (10 + 15 * hug)), 0) if hug > 0 else child.sh[i].rotation_euler
        lib.stand(gma)
        bend = ss((t - 1.1) / 0.6)
        gma.chest.rotation_euler.x = d(24 * bend)
        gma.neck.rotation_euler.x = d(12 * bend)
        for i, sx in enumerate((1, -1)):
            gma.sh[i].rotation_euler = (d(-20 - 50 * bend), d(-sx * (35 - 25 * hug)), d(-sx * 30 * hug))
            gma.el[i].rotation_euler = (d(-30 - 45 * hug), 0, 0)
        # tiny rocking embrace
        gma.hips.rotation_euler.z = d(4 * math.sin(t * 2.5) * hug)
        lib.face(child, f, smile=1.0, eyes_closed=0.85 * hug)
        lib.face(gma, f, smile=1.0, eyes_closed=0.6 * hug)
        laugh = ss((t - 1.0) / 0.5)
        lib.sit(gpa, 0.30, lean=-14 + 22 * laugh)
        for i, sx in enumerate((1, -1)):
            gpa.sh[i].rotation_euler = (d(-40), d(-sx * 18), 0)
            gpa.el[i].rotation_euler = (d(-55 - 10 * math.sin(t * 6) * laugh), 0, 0)
        head_look(gpa, door + Vector((0, -0.6, 1.0)), 0.9)
        lib.face(gpa, f, smile=1.0, mouth=0.25 * laugh * (0.5 + 0.5 * math.sin(t * 9)))
        v = ss(t / 3.6)
        R.aim(ctx.cam, (1.7 - 0.4 * v, -1.1 + 0.4 * v, 1.35), (-0.7, 2.4, 1.05 + 0.05 * v), focus=door + Vector((0, -0.8, 1.0)))
    return anim


# ------------------------------------------------------------ kitchen
def build_kitchen(ctx):
    mats = sets.M()
    K = sets.kitchen(mats)
    R.flat_world((0.5, 0.42, 0.33, 1), 0.25)
    sunl = R.sun(elev=28, azim=180, energy=6.5, color=(1.0, 0.78, 0.52), angle=1.5)
    R.point("fill", (-59.5, -2.5, 1.8), 120, color=(1, 0.8, 0.6), radius=1.5, kind='AREA', size=(2.0, 1.5)).rotation_euler = (d(70), 0, 0)
    R.point("fireglow", (-59.0, 1.6, 0.95), 35, color=(1, 0.45, 0.15), radius=0.2)
    R.point("bounce", (-60.3, 0.3, 2.6), 40, color=(1, 0.85, 0.7), radius=1.0)
    R.volume((5.0, 4.4, 2.9), (-60, 0, 1.45), density=0.035, color=(1, 0.92, 0.8))
    cam = R.camera(lens=35, fstop=2.8)
    child, gma = make_chars(ctx, ["child", "grandma"])
    gs, ks = K["gma_seat"], K["kid_seat"]
    lib.place(gma, (gs.x, gs.y, 0), 62); lib.sit(gma, gs.z)
    lib.place(child, (ks.x, ks.y, 0), -70); lib.sit(child, ks.z)
    plate = sets.plate_with_rice("plate", (0, 0, 0), mats)
    ctx.K, ctx.cam, ctx.mats, ctx.plate = K, cam, mats, plate
    return child, gma


def gma_feed_pose(ctx, gma, child, t, feed):
    """grandma holds plate on her lap with left hand; right hand to plate (0) or child's mouth (1)"""
    lib.sit(gma, ctx.K["gma_seat"].z, lean=10 + 8 * feed)
    bpy.context.view_layer.update()
    lap = gma.hips.matrix_world @ Vector((0.06, -0.3, 0.06))
    ctx.plate.location = lap; ctx.plate.rotation_euler = (0, 0, 0)
    reach(gma, 0, lap + Vector((0.08, 0.02, 0.02)), bend=30)
    mouth = headpos(child) + (child.root.matrix_world.to_3x3() @ Vector((0, -child.R * 1.05, -child.R * 0.45)))
    tgt = lap + Vector((0, 0, 0.05)) + (mouth - lap - Vector((0, 0, 0.05))) * feed
    if feed < 0.05:
        tgt += Vector((0.04 * math.sin(t * 5), 0.04 * math.cos(t * 5), 0))   # mixing rice
    reach(gma, 1, tgt, bend=20 + 20 * (1 - feed))


def shot_s2_wide(ctx):
    child, gma = build_kitchen(ctx)
    c = ctx.cue("s2_gma1")
    def anim(f, t):
        gma_feed_pose(ctx, gma, child, t, 0.0)
        lib.sit(child, ctx.K["kid_seat"].z)
        # the child bounces with excitement, clapping lightly
        for i, sx in enumerate((1, -1)):
            child.sh[i].rotation_euler = (d(-45), d(-sx * 10), d(-sx * 25))
            child.el[i].rotation_euler = (d(-60 - 12 * abs(math.sin(t * 5))), 0, 0)
        child.hips.location.z += 0.012 * abs(math.sin(t * 5))
        head_look(child, headpos(gma), 0.9)
        head_look(gma, headpos(child), 0.85)
        lib.face(gma, f, mouth=ctx.mouth("grandma", t), smile=0.85, gaze=gaze_at(gma, headpos(child)))
        lib.face(child, f, smile=1.0, brows=0.5, gaze=gaze_at(child, headpos(gma)))
        u = ss(t / 5.0)
        R.aim(ctx.cam, (-59.6 + 0.2 * u, -2.5 + 0.5 * u, 1.35 - 0.1 * u), (-59.85, 0.2, 0.72), focus=headpos(gma))
    return anim


def shot_s2_child(ctx):
    child, gma = build_kitchen(ctx)
    c = ctx.cue("s2_child")
    ctx.cam.data.lens = 55; ctx.cam.data.dof.aperture_fstop = 1.8
    def anim(f, t):
        feed = ss(t / 0.6) * (1 - ss((t - 1.1) / 0.5))
        gma_feed_pose(ctx, gma, child, t, feed)
        lib.sit(child, ctx.K["kid_seat"].z)
        for i, sx in enumerate((1, -1)):
            child.sh[i].rotation_euler = (d(-30), d(-sx * 10), 0)
            child.el[i].rotation_euler = (d(-70), 0, 0)
        chew = 0.0
        if 0.4 < t < 0.95:
            mo = 0.9
        elif 1.0 < t < c["start"]:
            mo = 0.0; chew = 1.0
        else:
            mo = ctx.mouth("child", t)
        head_look(child, headpos(gma), 0.7)
        child.head.rotation_euler.x += d(-6 * ss(t / 0.5) * (1 - ss((t - 1.0) / 0.3)))
        happy = ss((t - 1.0) / 0.3) * (1 - ss((t - c["start"]) / 0.3))
        lib.face(child, f, mouth=mo + 0.15 * chew * abs(math.sin(t * 12)), smile=1.0, eyes_closed=0.9 * happy, brows=0.4,
                 gaze=gaze_at(child, headpos(gma)))
        lib.face(gma, f, smile=0.9)
        hp = headpos(child)
        fw = child.root.matrix_world.to_3x3() @ Vector((0, -1, 0))
        R.aim(ctx.cam, hp + fw * 1.25 + Vector((0, -0.35, 0.08)), (hp.x, hp.y, hp.z - 0.1), focus=hp)
    return anim


def shot_s2_gma(ctx):
    child, gma = build_kitchen(ctx)
    ctx.cam.data.lens = 55; ctx.cam.data.dof.aperture_fstop = 1.8
    def anim(f, t):
        gma_feed_pose(ctx, gma, child, t, 0.35 * ss((t - 1.3) / 0.8))
        lib.sit(child, ctx.K["kid_seat"].z)
        head_look(gma, headpos(child), 0.9, extra=(0, -3))
        gma.head.rotation_euler.y = d(8 * math.sin(t * 1.0))
        lib.face(gma, f, mouth=ctx.mouth("grandma", t), smile=1.0, brows=0.5, gaze=gaze_at(gma, headpos(child)))
        lib.face(child, f, smile=1.0)
        hp = headpos(gma)
        u = ss(t / 4)
        R.aim(ctx.cam, (hp.x + 0.95, hp.y - 1.25 + 0.1 * u, hp.z), (hp.x, hp.y, hp.z - 0.12), focus=hp)
    return anim


# ------------------------------------------------------------ lane
LX = 120.0
def build_lane(ctx):
    mats = sets.M()
    L = sets.lane(mats)
    light_golden(elev=16, azim=230, energy=4.4)
    cam = R.camera(lens=30, fstop=4)
    gpa, child = make_chars(ctx, ["grandpa", "child"])
    ctx.L, ctx.cam, ctx.mats, ctx.palms = L, cam, mats, L["palms"]
    return gpa, child


def walk_pair(ctx, gpa, child, t, y, talk_up=None):
    lib.place(gpa, (LX + 0.28, y, 0), 0)
    lib.place(child, (LX - 0.28, y + 0.05, 0), 0)
    lib.stand(gpa); lib.stand(child)
    lib.walk(gpa, t, stride=20, arm=12, bob=0.015, speed=0.85, knee=25)
    lib.walk(child, t + 0.3, stride=30, arm=22, bob=0.025, speed=1.25, knee=40)
    bpy.context.view_layer.update()
    a = gpa.sh[1].parent.matrix_world @ gpa.sh[1].location
    b = child.sh[0].parent.matrix_world @ child.sh[0].location
    hold = (a + b) / 2 + Vector((0, -0.08, -0.32))
    reach(gpa, 1, hold, bend=10)
    reach(child, 0, hold, bend=5)


def shot_s3_walk(ctx):
    gpa, child = build_lane(ctx)
    c1, c2 = ctx.cue("s3_child1"), ctx.cue("s3_gpa")
    dur = ctx.shot["frames"] / FPS
    def anim(f, t):
        sets.sway(ctx.palms, t)
        y = 3.0 - 0.75 * t
        walk_pair(ctx, gpa, child, t, y)
        hc, hg = headpos(child), headpos(gpa)
        head_look(child, hg if t > c1["start"] - 0.3 else hc + Vector((0, -3, 0)), 0.8)
        head_look(gpa, hc if t > c1["start"] + 0.3 else hg + Vector((0, -3, -0.5)), 0.7)
        lib.face(child, f, mouth=ctx.mouth("child", t), smile=0.9, brows=0.5, gaze=gaze_at(child, hg))
        lib.face(gpa, f, mouth=ctx.mouth("grandpa", t), smile=0.85, gaze=gaze_at(gpa, hc))
        u = t / dur
        R.aim(ctx.cam, (LX + 0.9 - 0.4 * u, y - 4.6 + 0.6 * u, 1.05 + 0.1 * u), (LX, y, 0.95), focus=(LX, y, 1.0))
    return anim


def shot_s3_two(ctx):
    gpa, child = build_lane(ctx)
    ctx.cam.data.lens = 45; ctx.cam.data.dof.aperture_fstop = 2.2
    def anim(f, t):
        sets.sway(ctx.palms, t)
        y = -4.0 - 0.75 * t
        walk_pair(ctx, gpa, child, t + 8, y)
        hc, hg = headpos(child), headpos(gpa)
        head_look(child, hg, 0.9)
        head_look(gpa, hc, 0.8)
        moved = ss((t - 2.5) / 0.6)
        lib.face(child, f, mouth=ctx.mouth("child", t), smile=1.0, brows=0.6, gaze=gaze_at(child, hg))
        lib.face(gpa, f, smile=0.6 + 0.4 * moved, eyes_closed=0.35 * moved, gaze=gaze_at(gpa, hc))
        R.aim(ctx.cam, (LX - 1.35, y - 1.75, 0.95), (LX - 0.05, y, 1.05), focus=hc)
    return anim


def shot_s3_shop(ctx):
    gpa, child = build_lane(ctx)
    ctx.cam.data.lens = 30; ctx.cam.data.dof.aperture_fstop = 4
    def anim(f, t):
        sets.sway(ctx.palms, t)
        u = ss(t / 1.8)
        y = -13.8 - 1.9 * u
        if t < 1.8:
            walk_pair(ctx, gpa, child, t, y)
        else:
            lib.place(gpa, (LX + 0.1 - 0.2, y, 0), -60); lib.stand(gpa)
            lib.place(child, (LX - 0.45, y + 0.1, 0), -80); lib.stand(child)
            hop = max(0, math.sin((t - 2.4) * 7)) * ss((t - 2.4) / 0.1) * (1 - ss((t - 3.3) / 0.2))
            child.root.location.z = 0.05 * hop
            # grandpa points to the sweet jars, child reaches up happily
            gpa.sh[1].rotation_euler = (d(-70), d(10), 0); gpa.el[1].rotation_euler = (d(-10), 0, 0)
            child.sh[0].rotation_euler = (d(-150 * ss((t - 2.2) / 0.3)), d(-10), 0)
        shop = Vector((LX - 2.0, -16.0, 1.2))
        head_look(child, shop, 0.8); head_look(gpa, shop, 0.6)
        lib.face(child, f, smile=1.0, brows=0.7, mouth=0.3 * ss((t - 2.2) / 0.3))
        lib.face(gpa, f, smile=0.9)
        v = ss(t / 3.8)
        R.aim(ctx.cam, (LX + 1.6 - 0.3 * v, -12.6 - 0.4 * v, 1.55), (LX - 1.2, -16.0, 1.05), focus=(LX - 0.3, -15.6, 1.0))
    return anim


# ------------------------------------------------------------ bedroom (night)
def build_bedroom(ctx, night=True, aged=False):
    mats = sets.M()
    B = sets.bedroom(mats)
    o = B["origin"]
    if night:
        R.flat_world((0.02, 0.03, 0.06, 1), 1.0)
        moon = R.point("moon", (o.x - 2.6, o.y + 0.2, 1.7), 60, color=(0.5, 0.65, 1.0), radius=0.6, kind='AREA', size=(1.2, 1.2))
        moon.rotation_euler = (0, d(-80), 0)
        lamp = B["lamp"]["root"]
        bpy.context.view_layer.update()
        fl = B["lamp"]["flame"].matrix_world.translation
        ctx.lamp_light = R.point("lamplight", fl + Vector((0, 0, 0.05)), 45, color=(1.0, 0.55, 0.22), radius=0.04)
        R.point("lampfill", fl + Vector((-0.6, -1.4, 0.3)), 25, color=(1.0, 0.55, 0.25), radius=0.8)
        R.volume((4.6, 4.2, 2.9), (o.x, o.y, 1.45), density=0.012, color=(1, 0.8, 0.6))
    else:
        R.flat_world((0.55, 0.45, 0.35, 1), 0.25)
        R.sun(elev=16, azim=180, energy=6.0, color=(1.0, 0.68, 0.42), angle=1.0)
        R.point("fill", (o.x, o.y - 3.0, 1.8), 80, color=(1, 0.8, 0.6), radius=1.5, kind='AREA', size=(2.0, 1.5)).rotation_euler = (d(70), 0, 0)
        R.volume((4.6, 4.2, 2.9), (o.x, o.y, 1.45), density=0.05, color=(1, 0.9, 0.75))
        B["lamp"]["flame"].hide_render = True
        for ob in bpy.data.objects:
            if ob.name.startswith("lamp_flamecore"):
                ob.hide_render = True
    if aged:
        # empty bed: blanket folded, dust
        B["blanket"].scale = (1, 0.4, 1.4); B["blanket"].location.y += 0.55
    ctx.B = B
    ctx.cam = R.camera(lens=35, fstop=2.4)
    return B


def bed_pose(ctx, child, gma):
    B = ctx.B; bed = B["bed"]
    lib.lie(child, (bed.x, bed.y + 0.74 - 0.98, bed.z + 0.1), 0)
    B["blanket"].location = (bed.x, bed.y - 0.2, bed.z + 0.13)
    B["blanket"].scale = (0.95, 0.88, 3.4)
    lib.place(gma, (bed.x + 0.62, bed.y + 0.5, 0), -100)
    lib.sit(gma, 0.52)


def shot_s4_wide(ctx):
    build_bedroom(ctx)
    child, gma = make_chars(ctx, ["child", "grandma"])
    def anim(f, t):
        bed_pose(ctx, child, gma)
        ctx.lamp_light.data.energy = 45 * (1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 31))
        child.sh[0].rotation_euler = (d(-40), d(25), 0)
        head_look(child, headpos(gma), 0.6)
        head_look(gma, headpos(child), 0.8)
        lib.face(child, f, mouth=ctx.mouth("child", t), smile=0.8, brows=0.7, gaze=gaze_at(child, headpos(gma)))
        lib.face(gma, f, smile=0.85, gaze=gaze_at(gma, headpos(child)))
        o = ctx.B["origin"]
        u = ss(t / 5.5)
        bed = ctx.B["bed"]
        R.aim(ctx.cam, (bed.x - 1.25 + 0.15 * u, bed.y - 0.7 + 0.2 * u, 1.6 - 0.1 * u), (bed.x + 0.3, bed.y + 0.65, 0.85), focus=headpos(gma))
    return anim


def shot_s4_story(ctx):
    build_bedroom(ctx)
    child, gma = make_chars(ctx, ["child", "grandma"])
    ctx.cam.data.lens = 55; ctx.cam.data.dof.aperture_fstop = 1.8
    def anim(f, t):
        bed_pose(ctx, child, gma)
        ctx.lamp_light.data.energy = 45 * (1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 31))
        gest = 0.5 + 0.5 * math.sin(t * 2.2)
        gma.sh[1].rotation_euler = (d(-50 - 15 * gest), d(15), d(10))
        gma.el[1].rotation_euler = (d(-70), 0, d(20 * gest))
        hc = headpos(child)
        head_look(gma, hc, 0.8, extra=(0, 4 * math.sin(t)))
        lib.face(gma, f, mouth=ctx.mouth("grandma", t), smile=0.75, brows=0.8 * ss((t - 0.2) / 0.5), gaze=gaze_at(gma, hc))
        lib.face(child, f, smile=0.7)
        hp = headpos(gma)
        fw = gma.root.matrix_world.to_3x3() @ Vector((0, -1, 0))
        R.aim(ctx.cam, hp + fw * 1.2 + Vector((0, -0.45, -0.05)), (hp.x, hp.y, hp.z - 0.1), focus=hp)
    return anim


def shot_s4_eager(ctx):
    build_bedroom(ctx)
    child, gma = make_chars(ctx, ["child", "grandma"])
    ctx.cam.data.lens = 50; ctx.cam.data.dof.aperture_fstop = 1.8
    def anim(f, t):
        bed_pose(ctx, child, gma)
        ctx.lamp_light.data.energy = 45 * (1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 31))
        lift = ss(t / 0.3)
        child.chest.rotation_euler.x = d(-8 * lift)
        hg = headpos(gma)
        head_look(child, hg, 0.8)
        for i, sx in enumerate((1, -1)):
            child.sh[i].rotation_euler = (d(-60 * lift), d(-sx * 20), 0)
        lib.face(child, f, mouth=ctx.mouth("child", t), smile=0.9, brows=1.0, gaze=gaze_at(child, hg))
        lib.face(gma, f, smile=0.9)
        hp = headpos(child)
        R.aim(ctx.cam, (hp.x + 0.5, hp.y - 0.25, hp.z + 0.75), (hp.x, hp.y, hp.z), focus=hp)
    return anim


def shot_s4_sleep(ctx):
    build_bedroom(ctx)
    child, gma = make_chars(ctx, ["child", "grandma"])
    ctx.cam.data.lens = 40; ctx.cam.data.dof.aperture_fstop = 2.0
    c = ctx.cue("s4_gma2")
    dur = ctx.shot["frames"] / FPS
    def anim(f, t):
        bed_pose(ctx, child, gma)
        ctx.lamp_light.data.energy = 45 * (1 + 0.08 * math.sin(t * 13) + 0.05 * math.sin(t * 31))
        hc = headpos(child)
        gma.chest.rotation_euler.x = d(14)
        reach(gma, 1, hc + Vector((0.03 * math.sin(t * 2.0), 0.08 + 0.05 * math.sin(t * 2.0), child.R * 0.9)), bend=25)
        head_look(gma, hc, 0.9)
        sleepy = ss((t - c["start"] - 1.5) / 2.5)
        lib.face(gma, f, mouth=ctx.mouth("grandma", t), smile=0.9, gaze=gaze_at(gma, hc), eyes_closed=0.25)
        lib.face(child, f, smile=0.6, eyes_closed=sleepy, blink=0 if sleepy > 0.9 else None)
        head_look(child, headpos(gma), 0.5 * (1 - sleepy))
        o = ctx.B["origin"]
        # end: drift to the flickering lamp flame
        lamp = ctx.B["lamp"]["flame"].matrix_world.translation
        u = ss((t - (dur - 2.8)) / 2.6)
        start_pos = Vector((hc.x - 1.0, hc.y - 1.0, hc.z + 0.55)); start_t = (hc + headpos(gma)) / 2
        end_pos = lamp + Vector((-0.25, -0.45, 0.05))
        pos = start_pos.lerp(end_pos, u); tgt = start_t.lerp(lamp, u)
        R.aim(ctx.cam, pos, tgt, focus=tgt)
    return anim


# ------------------------------------------------------------ years later
def age_world(mats, amount=1.0):
    """weather the house: darker stained walls, mossy tiles"""
    for key, (a, b) in dict(wall=("#b8ab92", "#8a7f6a"), tile=("#6e3a28", "#3f2a1e"), laterite=("#6e3a26", "#4e2a1a")).items():
        m = mats[key]
        ramp = [n for n in m.node_tree.nodes if n.type == 'VALTORGB'][0]
        if not hasattr(m, "_orig"):
            pass
        c0 = ramp.color_ramp.elements[0].color[:]; c1 = ramp.color_ramp.elements[1].color[:]
        ramp.color_ramp.elements[0].color = lerp(c0, lib.srgb(a), amount)
        ramp.color_ramp.elements[1].color = lerp(c1, lib.srgb(b), amount)


def shot_s5_timelapse(ctx):
    mats = build_title(ctx)
    sun = [o for o in bpy.data.objects if o.type == 'LIGHT'][0]
    world = bpy.context.scene.world.node_tree
    sky = [n for n in world.nodes if n.type == 'TEX_SKY'][0]
    bg = [n for n in world.nodes if n.type == 'BACKGROUND'][0]
    ctx.cam.data.lens = 26
    targets = dict(wall=("#b8ab92", "#8a7f6a"), tile=("#6e3a28", "#3f2a1e"), laterite=("#6e3a26", "#4e2a1a"))
    orig = {k: [tuple(e.color) for e in [n for n in mats[k].node_tree.nodes if n.type == 'VALTORGB'][0].color_ramp.elements] for k in targets}
    def anim(f, t):
        u = t / 5.5
        sets.sway(ctx.palms, t * 3, amp=1.0 + 2.5 * math.sin(math.pi * min(1, u * 1.4)))
        # days and seasons race past: sun sweeps repeatedly, storm in the middle, house weathers
        cyc = (u * 3.2) % 1.0
        elev = -5 + 60 * math.sin(math.pi * cyc)
        storm = math.sin(math.pi * min(1, max(0, (u - 0.25) / 0.5)))
        sun.rotation_euler = (0, d(90 - max(elev, -5)), d(120 + 180 * cyc))
        sun.data.energy = max(0, 4.5 * math.sin(math.pi * cyc)) * (1 - 0.8 * storm)
        sky.sun_elevation = d(max(elev, -4)); sky.sun_rotation = d(30 + 180 * cyc)
        bg.inputs[1].default_value = (0.08 + 0.5 * max(0, math.sin(math.pi * cyc))) * (1 - 0.6 * storm)
        for k, (a, b) in targets.items():
            ramp = [n for n in mats[k].node_tree.nodes if n.type == 'VALTORGB'][0]
            ramp.color_ramp.elements[0].color = lerp(orig[k][0], lib.srgb(a), ss(u))
            ramp.color_ramp.elements[1].color = lerp(orig[k][1], lib.srgb(b), ss(u))
        ctx.chair["rock"].rotation_euler.x = d(2.5 * math.sin(t * 4))
        v = ss(u)
        R.aim(ctx.cam, (1.5 - 1.0 * v, -12 + 5.5 * v, 2.2 - 0.6 * v), (-1.0, 2.5, 1.4), focus=(-2.5, 2.5, 1.0))
    return anim


def shot_s5_return(ctx):
    mats = build_title(ctx, dusk=True)
    age_world(mats)
    adult, = make_chars(ctx, ["adult"])
    ctx.cam.data.lens = 32; ctx.cam.data.dof.aperture_fstop = 2.8
    def anim(f, t):
        sets.sway(ctx.palms, t, amp=1.4)
        walk_t = min(t, 3.4)
        slow = ss((t - 2.4) / 1.0)
        y = -8.0 + 0.95 * walk_t - 0.3 * slow
        lib.place(adult, (0.35, y, 0), 180)
        lib.stand(adult)
        if t < 3.4:
            lib.walk(adult, t, stride=22 * (1 - slow), arm=14 * (1 - slow), bob=0.018 * (1 - slow), speed=0.9, knee=30 * (1 - slow))
        # he stops and looks up at the old house
        head_look(adult, Vector((-1.5, 3.0, 2.0 + 0.6 * ss((t - 3.4) / 1.0))), 0.9)
        lib.face(adult, f, smile=0.15, brows=-0.2)
        hp = headpos(adult)
        u = ss(t / 5.0)
        R.aim(ctx.cam, (1.3 + 0.2 * u, hp.y - 2.6 - 0.4 * u, 1.15), (hp.x - 0.6, hp.y + 5, 1.6), focus=hp)
    return anim


def shot_s5_face(ctx):
    build_bedroom(ctx, night=False, aged=True)
    adult, = make_chars(ctx, ["adult"])
    o = ctx.B["origin"]
    img = os.path.join(ROOT, "build", "photo.png")
    ctx.cam.data.lens = 55; ctx.cam.data.dof.aperture_fstop = 1.8
    photo = sets.photo_frame("held", (0, 0, 0), (0, 0, 0), img, w=0.24, h=0.18, mats=sets.M(), faded=0.3)
    def anim(f, t):
        lib.place(adult, (o.x - 1.4, o.y + 0.2, 0), -60)
        hold_photo(adult, photo, t)
        lib.face(adult, f, smile=0.25 * ss((t - 2.5) / 1.0), brows=-0.3, eyes_closed=0.35,
                 gaze=(0, -18))
        hp = headpos(adult)
        u = ss(t / 4)
        fwd = adult.root.matrix_world.to_3x3() @ Vector((0, -1, 0))
        side = adult.root.matrix_world.to_3x3() @ Vector((1, 0, 0))
        R.aim(ctx.cam, hp + fwd * (0.9 - 0.12 * u) + side * 0.25 + Vector((0, 0, -0.18)), hp + Vector((0, 0, -0.05)), focus=hp)
    return anim


def hold_photo(adult, photo, t):
    lib.stand(adult)
    adult.neck.rotation_euler.x = d(22); adult.head.rotation_euler.x = d(14)
    bpy.context.view_layer.update()
    M3 = adult.root.matrix_world.to_3x3()
    chest = adult.chest.matrix_world.translation
    pc = chest + M3 @ Vector((0, -0.36, 0.22 + 0.005 * math.sin(t * 1.3)))
    photo.location = pc
    photo.rotation_euler = (adult.root.rotation_euler.to_matrix() @ Vector((0, 0, 0))).to_track_quat('Z', 'Y').to_euler()
    photo.rotation_euler = (d(-50), 0, adult.root.rotation_euler.z)
    for i, sx in enumerate((1, -1)):
        reach(adult, i, pc + M3 @ Vector((sx * 0.13, 0.03, -0.02)), bend=75)


def shot_s5_photo(ctx):
    build_bedroom(ctx, night=False, aged=True)
    adult, = make_chars(ctx, ["adult"])
    o = ctx.B["origin"]
    img = os.path.join(ROOT, "build", "photo.png")
    ctx.cam.data.lens = 50; ctx.cam.data.dof.aperture_fstop = 2.2
    photo = sets.photo_frame("held", (0, 0, 0), (0, 0, 0), img, w=0.24, h=0.18, mats=sets.M(), faded=0.3)
    dur = ctx.shot["frames"] / FPS
    def anim(f, t):
        lib.place(adult, (o.x - 1.4, o.y + 0.2, 0), -60)
        hold_photo(adult, photo, t)
        lib.face(adult, f, smile=0.2, eyes_closed=0.35, gaze=(0, -18))
        bpy.context.view_layer.update()
        pc = photo.matrix_world.translation
        hp = headpos(adult)
        u = ss(t / dur)
        # over-the-shoulder push-in onto the photograph
        M3 = adult.root.matrix_world.to_3x3()
        n = photo.matrix_world.to_3x3() @ Vector((0, -1, 0))
        dist = 0.62 - 0.22 * u
        R.aim(ctx.cam, pc + n * dist + (hp - pc).normalized() * 0.06, pc, focus=pc)
    return anim


# ------------------------------------------------------------ memories remain
def shot_s6_veranda(ctx):
    mats = build_title(ctx, dusk=True)
    age_world(mats)
    ctx.cam.data.lens = 40; ctx.cam.data.dof.aperture_fstop = 2.4
    ch = ctx.H["chair"]
    def anim(f, t):
        sets.sway(ctx.palms, t, amp=1.3)
        ctx.chair["rock"].rotation_euler.x = d(2.2 * math.sin(t * 1.9))
        u = ss(t / 6)
        R.aim(ctx.cam, (ch.x + 0.9 - 0.3 * u, ch.y - 3.6 + 1.0 * u, 1.2), (ch.x, ch.y, 0.85), focus=ch + Vector((0, 0, 0.6)))
    return anim


def shot_s6_toys(ctx):
    mats = sets.M()
    build_bedroom(ctx, night=False, aged=True)
    o = ctx.B["origin"]
    sets.toys("toys", (o.x - 0.6, o.y - 0.8, 0.0), mats)
    ctx.cam.data.lens = 35; ctx.cam.data.dof.aperture_fstop = 2.0
    def anim(f, t):
        u = ss(t / 5.5)
        tg = Vector((o.x - 0.55, o.y - 0.6, 0.1))
        R.aim(ctx.cam, (o.x + 0.25 - 0.45 * u, o.y - 1.75 + 0.15 * u, 0.55 - 0.1 * u), tg, focus=tg)
    return anim


def shot_s6_photo(ctx):
    mats = sets.M()
    build_bedroom(ctx, night=False, aged=True)
    o = ctx.B["origin"]
    img = os.path.join(ROOT, "build", "photo.png")
    fr = sets.photo_frame("wallphoto", (o.x + 0.3, o.y + 2.06, 1.75), (0, 0, 0), img, w=0.56, h=0.42, mats=mats, faded=0.35)
    fr.location.y = o.y + 1.99
    # garland of dried flowers on the frame (a gentle sign of remembrance)
    for k in range(13):
        a = math.pi * k / 12
        lib.sphere(f"garland{k}", 0.028, (o.x + 0.3 + 0.33 * math.cos(a), o.y + 1.96, 1.75 + 0.26 - 0.3 * math.sin(a) * 0.0 + 0.0 - (0.0)),
                   (1, 1, 1), lib.mat("marigold", "#d98a1c", 0.6))
    ctx.cam.data.lens = 50; ctx.cam.data.dof.aperture_fstop = 2.8
    def anim(f, t):
        u = ss(t / 5)
        tg = Vector((o.x + 0.3, o.y + 2.0, 1.75))
        R.aim(ctx.cam, (o.x + 0.3 - 0.2 + 0.2 * u, o.y + 0.2 + 0.55 * u, 1.55 + 0.1 * u), tg, focus=tg)
    return anim


def shot_s6_final(ctx):
    mats = build_title(ctx, final=True)
    age_world(mats, 0.7)
    ctx.cam.data.lens = 26; ctx.cam.data.dof.aperture_fstop = 8
    dur = ctx.shot["frames"] / FPS
    def anim(f, t):
        sets.sway(ctx.palms, t)
        ctx.chair["rock"].rotation_euler.x = d(1.5 * math.sin(t * 1.7))
        u = ss(t / dur)
        R.aim(ctx.cam, lerp((0.4, -6.5, 1.5), (0.0, -30, 11), u), lerp((0, 2.5, 2.0), (0, 3, 3.2), u))
    return anim


# ------------------------------------------------------------ family photo still
def shot_photo(ctx):
    build_title(ctx)
    child, gma, gpa = make_chars(ctx, ["child", "grandma", "grandpa"])
    door = ctx.H["door"]
    lib.place(gma, door + Vector((-0.55, -1.0, 0)), 0)
    lib.place(gpa, door + Vector((0.55, -1.0, 0)), 0)
    lib.place(child, door + Vector((0.0, -1.4, 0)), 0)
    for P in (gma, gpa, child):
        lib.stand(P)
    ctx.cam.data.lens = 50; ctx.cam.data.dof.aperture_fstop = 5.6
    def anim(f, t):
        gma.sh[1].rotation_euler = (d(-25), d(-10), d(-30)); gma.el[1].rotation_euler = (d(-40), 0, 0)
        gpa.sh[0].rotation_euler = (d(-25), d(10), d(30)); gpa.el[0].rotation_euler = (d(-40), 0, 0)
        for P in (gma, gpa, child):
            lib.face(P, 0, smile=1.0, blink=0)
        R.aim(ctx.cam, (0.0, door.y - 5.2, 1.3), (0, door.y - 1.0, 1.15))
    return anim


SHOT_FUNCS = {k[0]: globals()["shot_" + k[0]] for k in SHOTS}
SHOT_FUNCS["photo"] = shot_photo
