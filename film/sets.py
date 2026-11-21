"""Environments and props: Kerala tharavadu house + courtyard, village lane
with paddy field and petti-kada shop, kitchen, bedroom, and props."""
import math, random
import bpy, bmesh
from mathutils import Vector
from lib import (mat, noise_mat, sphere, cyl, box, torus, tube, plane, loft, empty, srgb, link, _finish)

rnd = random.Random(42)

# ------------------------------------------------------------------ materials
def M():
    return dict(
        wall=noise_mat("wall", "#e9dcc0", "#d9c7a3", scale=3, rough=0.9, bump=0.15),
        laterite=noise_mat("laterite", "#9a4a2b", "#7a3420", scale=14, rough=0.95, bump=0.6),
        redoxide=mat("redoxide", "#7d2418", rough=0.18, coat=0.6),
        wood=noise_mat("wood", "#5b3520", "#3e2213", scale=4, rough=0.55, bump=0.1, wave=dict(type='BANDS', dir='Z', dist=6)),
        woodlight=noise_mat("woodlight", "#8a5a34", "#6c4325", scale=5, rough=0.5, bump=0.1, wave=dict(type='BANDS', dir='Z', dist=5)),
        tile=noise_mat("tile", "#a7482a", "#6e2a17", scale=22, rough=0.75, bump=0.8, wave=dict(type='BANDS', dir='X', dist=0.6), detail=2),
        sand=noise_mat("sand", "#cfae84", "#b38f66", scale=6, rough=0.95, bump=0.3),
        path=noise_mat("pathm", "#b2643c", "#8f4b2b", scale=7, rough=0.95, bump=0.4),
        grass=noise_mat("grassm", "#5e7d2a", "#3e5a1c", scale=3, rough=0.95, bump=0.2),
        leaf=mat("leaf", "#4f7a22", rough=0.6, sss=0.15),
        leaf2=mat("leaf2", "#6a8f2a", rough=0.6, sss=0.15),
        leafdark=mat("leafdark", "#2f5216", rough=0.7),
        frond=mat("frond", "#5e8a24", rough=0.55, sss=0.2),
        trunk=noise_mat("trunk", "#7a6a55", "#4e4236", scale=30, rough=0.9, bump=0.8, wave=dict(type='RINGS', dir='Z', dist=1)),
        coconut=mat("coconut", "#7a8a2a", rough=0.5),
        brass=mat("brass", "#c9932e", rough=0.22, metal=1.0),
        steel=mat("steel", "#cfd3d6", rough=0.15, metal=1.0),
        clay=noise_mat("clay", "#8a4a2c", "#6a3520", scale=10, rough=0.8, bump=0.3),
        black=mat("blackpot", "#1b1512", rough=0.5),
        rice=noise_mat("rice", "#f7f2e6", "#e6dccb", scale=60, rough=0.6, bump=1.0),
        cloth=mat("whitecloth", "#f1ece0", rough=0.85, sheen=0.5),
        dark=mat("darkint", "#120b07", rough=1.0),
        hibiscus=mat("hibiscus", "#c3121b", rough=0.5, sss=0.2),
        water=mat("water", "#5c7a78", rough=0.04, spec=0.8),
    )


# ------------------------------------------------------------------ vegetation
def palm(name, loc, h=None, lean=None, seed=0, mats=None):
    r = random.Random(seed)
    h = h or r.uniform(7, 11)
    lean = lean if lean is not None else (r.uniform(-0.12, 0.12), r.uniform(-0.12, 0.12))
    pts = []
    for i in range(12):
        t = i / 11
        pts.append((loc[0] + lean[0] * h * t ** 1.6, loc[1] + lean[1] * h * t ** 1.6, loc[2] + h * t))
    tube(f"{name}_trunk", pts, 0.19, mats["trunk"], mseg=10, r_end=0.12)
    top = Vector(pts[-1])
    crown = empty(f"{name}_crown", top)
    sphere(f"{name}_head", 0.28, (0, 0, -0.05), (1, 1, 0.8), mats["leafdark"], crown, segs=12)
    for k in range(5):
        a = k * 2 * math.pi / 5 + r.uniform(0, 1)
        sphere(f"{name}_nut{k}", 0.12, (math.cos(a) * 0.25, math.sin(a) * 0.25, -0.25), (1, 1, 1.1), mats["coconut"], crown, segs=10)
    fronds = []
    n = r.randint(12, 15)
    for k in range(n):
        a = k * 2 * math.pi / n + r.uniform(-0.2, 0.2)
        lift = r.uniform(-0.1, 0.9)
        piv = empty(f"{name}_fp{k}", (0, 0, 0), crown, rot=(0, 0, a))
        frond_mesh(f"{name}_fr{k}", piv, length=r.uniform(3.0, 4.2), lift=lift, m=mats["frond" if k % 3 else "leaf"], seed=seed * 100 + k)
        fronds.append(piv)
    return dict(crown=crown, fronds=fronds, top=top, phase=r.uniform(0, 6.28))


def frond_mesh(name, parent, length=3.5, lift=0.4, m=None, seed=0):
    r = random.Random(seed)
    bm = bmesh.new()
    nseg = 16
    spine = []
    for i in range(nseg + 1):
        t = i / nseg
        x = length * t
        z = lift * t * 1.4 - 2.2 * (t ** 2) * (0.6 + 0.4 * (1 - lift))
        spine.append(Vector((x, 0, z)))
    for i in range(1, nseg):
        p = spine[i]; t = i / nseg
        ll = 0.95 * math.sin(math.pi * min(1, t * 1.15)) + 0.12
        for sgn in (1, -1):
            droop = -0.35 - 0.25 * t
            tip = p + Vector((0.28 * ll, sgn * ll, droop * ll))
            w = 0.05
            v1 = bm.verts.new(p + Vector((-w, 0, 0))); v2 = bm.verts.new(p + Vector((w, 0, 0)))
            v3 = bm.verts.new(tip + Vector((0.02, 0, 0)))
            bm.faces.new((v1, v2, v3))
    for i in range(nseg):
        a, b = spine[i], spine[i + 1]
        v = [bm.verts.new(a + Vector((0, 0.025, 0))), bm.verts.new(b + Vector((0, 0.015, 0))),
             bm.verts.new(b + Vector((0, -0.015, 0))), bm.verts.new(a + Vector((0, -0.025, 0)))]
        bm.faces.new(v)
    ob = _finish(name, bm, m, parent, (0, 0, 0), (0, 0, 0), (1, 1, 1), smooth=True)
    return ob


def banana(name, loc, seed, mats):
    r = random.Random(seed)
    h = r.uniform(2.2, 3.2)
    cyl(f"{name}_st", 0.13, 0.09, h, (loc[0], loc[1], loc[2] + h / 2), mats["leaf2"])
    tops = []
    for k in range(7):
        a = k * 2 * math.pi / 7 + r.uniform(-0.3, 0.3)
        piv = empty(f"{name}_lp{k}", (loc[0], loc[1], loc[2] + h), None, rot=(0, 0, a))
        bm = bmesh.new()
        L = r.uniform(1.6, 2.2)
        rows = []
        for i in range(9):
            t = i / 8; x = L * t; z = 0.9 * t - 1.3 * t * t
            w = 0.38 * math.sin(math.pi * min(t * 1.1, 1)) + 0.02
            rows.append([bm.verts.new((x, -w, z - 0.08 * w)), bm.verts.new((x, 0, z)), bm.verts.new((x, w, z - 0.08 * w))])
        for i in range(8):
            for j in range(2):
                bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
        _finish(f"{name}_lf{k}", bm, mats["leaf"], piv, (0, 0, 0), (r.uniform(-0.2, 0.2), 0, 0), (1, 1, 1))
        tops.append(piv)
    return tops


def bush(name, loc, size, seed, mats, flowers=False):
    r = random.Random(seed)
    for k in range(r.randint(4, 7)):
        o = (loc[0] + r.uniform(-size, size) * 0.6, loc[1] + r.uniform(-size, size) * 0.6, loc[2] + size * r.uniform(0.4, 0.9))
        sphere(f"{name}_{k}", size * r.uniform(0.5, 0.8), o, (1, 1, 0.85), mats["leafdark" if k % 2 else "leaf"], segs=14)
    if flowers:
        for k in range(r.randint(4, 9)):
            o = (loc[0] + r.uniform(-size, size) * 0.8, loc[1] - size * 0.6 + r.uniform(-0.2, 0.2), loc[2] + size * r.uniform(0.6, 1.4))
            sphere(f"{name}_f{k}", 0.07, o, (1, 1, 0.6), mats["hibiscus"], segs=8)


def grass_field(name, center, size, count, mats, seed=1, h=0.18, exclude=None, color="grass_blade"):
    """instanced grass tufts via a particle system on a plane"""
    pl = plane(name, size[0], size[1], center, mats["grass"], subdiv=1)
    tuft = make_tuft(f"{name}_tuft", h, color)
    ps = pl.modifiers.new("grass", 'PARTICLE_SYSTEM').particle_system
    st = ps.settings
    st.type = 'HAIR'; st.count = count; st.use_advanced_hair = True
    st.render_type = 'OBJECT'; st.instance_object = tuft
    st.particle_size = 1.0; st.size_random = 0.5
    st.use_rotations = True; st.rotation_mode = 'GLOB_Z'; st.phase_factor_random = 2.0
    st.hair_length = 1.0
    ps.seed = seed
    tuft.hide_render = True
    tuft.location = (0, 0, -50)
    return pl


def make_tuft(name, h, color):
    bm = bmesh.new()
    r = random.Random(3)
    for k in range(7):
        a = r.uniform(0, 6.28); lean = r.uniform(0.1, 0.4)
        hh = h * r.uniform(0.6, 1.2)
        base = Vector((r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03), 0))
        tip = base + Vector((math.cos(a) * lean * hh, math.sin(a) * lean * hh, hh))
        side = Vector((-math.sin(a), math.cos(a), 0)) * 0.012
        bm.faces.new((bm.verts.new(base - side), bm.verts.new(base + side), bm.verts.new(tip)))
    m = mat(color, "#5f8a2a" if color == "grass_blade" else "#7aa832", rough=0.6, sss=0.2)
    return _finish(name, bm, m, None, (0, 0, 0), (0, 0, 0), (1, 1, 1))


# ------------------------------------------------------------------ props
def chaarukasera(name, loc, yaw, mats, rocker=True):
    """Kerala easy chair with long arms and a cloth sling, on gentle rockers"""
    root = empty(f"{name}_root", loc, None, rot=(0, 0, math.radians(yaw)))
    rk = empty(f"{name}_rock", (0, 0, 0), root)
    w = mats["wood"]
    if rocker:
        for sx in (1, -1):
            pts = [(sx * 0.3, -0.55 + 1.3 * t, 0.05 + 0.35 * (t - 0.5) ** 2) for t in [i / 10 for i in range(11)]]
            tube(f"{name}_rocker{sx}", pts, 0.025, w, rk, mseg=8)
    for sx in (1, -1):
        cyl(f"{name}_legf{sx}", 0.025, 0.025, 0.5, (sx * 0.3, -0.35, 0.28), w, rk)
        cyl(f"{name}_legb{sx}", 0.025, 0.025, 1.05, (sx * 0.3, 0.45, 0.55), w, rk, rot=(math.radians(-28), 0, 0))
        # long arm rests that stick out in front (the signature of a chaarukasera)
        box(f"{name}_arm{sx}", (0.07, 1.25, 0.04), (sx * 0.34, -0.25, 0.58), w, rk, bevel=0.01)
    box(f"{name}_front", (0.62, 0.04, 0.05), (0, -0.35, 0.3), w, rk)
    box(f"{name}_back", (0.62, 0.05, 0.05), (0, 0.66, 1.0), w, rk)
    # cloth sling (striped)
    stripe = noise_mat("sling", "#2e5f8a", "#e9e2cf", scale=12, rough=0.9, bump=0.0, wave=dict(type='BANDS', dir='X', dist=0), detail=0)
    pts = []
    bm = bmesh.new(); rows = []
    for i in range(12):
        t = i / 11
        y = -0.33 + 1.0 * t
        z = 0.32 - 0.12 * math.sin(math.pi * min(t * 1.6, 1)) + max(0, (t - 0.45)) * 1.25
        rows.append([bm.verts.new((x, y, z - 0.02 * (1 - abs(x) / 0.28))) for x in (-0.28, -0.1, 0.1, 0.28)])
    for i in range(11):
        for j in range(3):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    sl = _finish(f"{name}_sling", bm, stripe, rk, (0, 0, 0), (0, 0, 0), (1, 1, 1))
    sl.modifiers.new("solid", 'SOLIDIFY').thickness = 0.01
    return dict(root=root, rock=rk)


def nilavilakku(name, loc, mats, scale=1.0, flame=True):
    root = empty(f"{name}_root", loc)
    root.scale = (scale, scale, scale)
    b = mats["brass"]
    pts = [(0, 0, 0)]
    prof = [(0.0, 0.16), (0.03, 0.16), (0.05, 0.10), (0.09, 0.05), (0.2, 0.035), (0.35, 0.03), (0.42, 0.05), (0.5, 0.035),
            (0.62, 0.03), (0.66, 0.09), (0.69, 0.13), (0.71, 0.12), (0.72, 0.03), (0.8, 0.02), (0.88, 0.04), (0.92, 0.0)]
    loft(f"{name}_body", [(z, r, r) for z, r in prof], b, root, seg=28, power=2.0)
    fl = None
    if flame:
        fm = mat("flame", "#ffb347", emit="#ffa040", emit_str=40.0)
        fl = sphere(f"{name}_flame", 0.022, (0.10, 0, 0.75), (0.8, 0.8, 2.0), fm, root, segs=12)
        sphere(f"{name}_flamecore", 0.012, (0.10, 0, 0.735), (0.8, 0.8, 1.6), mat("flamecore", "#fff6d0", emit="#fff2c0", emit_str=60.0), root, segs=8)
    return dict(root=root, flame=fl)


def plate_with_rice(name, loc, mats, parent=None):
    root = empty(f"{name}_root", loc, parent)
    cyl(f"{name}_plate", 0.15, 0.13, 0.02, (0, 0, 0.01), mats["steel"], root, segs=32)
    sphere(f"{name}_rice", 0.09, (0.02, 0.01, 0.025), (1.1, 1, 0.35), mats["rice"], root, segs=20)
    sphere(f"{name}_curry", 0.045, (-0.07, -0.04, 0.025), (1, 1, 0.3), mat("sambar", "#c46b1d", 0.3, coat=0.5), root, segs=14)
    sphere(f"{name}_thoran", 0.04, (-0.06, 0.07, 0.025), (1, 1, 0.3), mat("thoran", "#9ab83a", 0.7), root, segs=14)
    sphere(f"{name}_pappadam", 0.055, (0.07, -0.08, 0.035), (1, 1, 0.1), mat("pappadam", "#f0d79a", 0.7), root, segs=16)
    return root


def toys(name, loc, mats):
    root = empty(f"{name}_root", loc)
    # wooden spinning top (pambaram)
    top_m = noise_mat("topm", "#c8461d", "#f0b030", scale=20, wave=dict(type='RINGS', dir='Z', dist=0), detail=0, bump=0)
    t = empty(f"{name}_top", (0.0, 0.0, 0.0), root, rot=(0, math.radians(70), 0.3))
    cyl(f"{name}_topc", 0.005, 0.06, 0.08, (0, 0, 0.04), top_m, t, segs=20)
    sphere(f"{name}_toph", 0.06, (0, 0, 0.08), (1, 1, 0.5), top_m, t, segs=20)
    # small red toy car
    car = empty(f"{name}_car", (0.35, 0.12, 0), root, rot=(0, 0, 0.6))
    red = mat("toycar", "#c8201e", 0.25, coat=1.0)
    box(f"{name}_carb", (0.22, 0.1, 0.06), (0, 0, 0.06), red, car, bevel=0.015)
    box(f"{name}_carc", (0.12, 0.09, 0.05), (-0.01, 0, 0.11), red, car, bevel=0.015)
    for sx in (1, -1):
        for sy in (1, -1):
            cyl(f"{name}_w{sx}{sy}", 0.03, 0.03, 0.02, (sx * 0.07, sy * 0.055, 0.03), mats["black"], car, rot=(math.radians(90), 0, 0))
    # ball
    ball_m = noise_mat("ballm", "#2a6fc9", "#f2d33a", scale=3, wave=dict(type='BANDS', dir='Z', dist=0), detail=0, bump=0)
    sphere(f"{name}_ball", 0.08, (-0.3, 0.25, 0.08), (1, 1, 1), ball_m, root)
    # little wooden elephant
    el = empty(f"{name}_ele", (0.1, 0.45, 0), root, rot=(0, 0, -0.5))
    w = mats["woodlight"]
    sphere(f"{name}_eb", 0.09, (0, 0, 0.12), (1.3, 0.9, 0.9), w, el)
    sphere(f"{name}_eh", 0.06, (-0.12, 0, 0.17), (1, 1, 1), w, el)
    tube(f"{name}_etr", [(-0.17, 0, 0.17), (-0.2, 0, 0.1), (-0.19, 0, 0.04)], 0.018, w, el)
    for sx in (1, -1):
        sphere(f"{name}_ee{sx}", 0.05, (-0.1, sx * 0.06, 0.18), (0.4, 1, 1.1), w, el)
        for sy in (1, -1):
            cyl(f"{name}_el{sx}{sy}", 0.025, 0.025, 0.08, (sx * 0.07, sy * 0.045, 0.04), w, el)
    return root


def photo_frame(name, loc, rot, img_path, w=0.42, h=0.32, mats=None, faded=0.25, parent=None):
    from lib import image_mat
    root = empty(f"{name}_root", loc, parent, rot=rot)
    fr = mats["wood"]
    box(f"{name}_fr", (w + 0.06, 0.025, h + 0.06), (0, 0.0, 0), fr, root, bevel=0.008)
    pm = image_mat(f"{name}_img", img_path, rough=0.35, faded=faded)
    p = plane(f"{name}_pic", w, h, (0, -0.014, 0), pm, root, rot=(math.radians(90), 0, 0))
    # UVs for plane: create_grid gives UVs only if calc_uvs; add simple projection
    me = p.data
    uvl = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (v.x / w + 0.5, v.y / h + 0.5)
    return root


# ------------------------------------------------------------------ the house
def house(mats, door_open=True):
    """tharavadu centred at x=0, front wall y=3.5, veranda front edge y=1.3"""
    H = dict()
    pl = 0.45
    # plinth (laterite) + floors
    box("plinth", (11.2, 9.3, pl), (0, 5.85, pl / 2), mats["laterite"])
    box("verfloor", (11.0, 2.2, 0.03), (0, 2.4, pl + 0.015), mats["redoxide"])
    box("housefloor", (10.6, 6.5, 0.03), (0, 6.75, pl + 0.015), mats["redoxide"])
    # steps
    for k in range(3):
        box(f"step{k}", (2.0, 0.32, pl / 3 * (k + 1)), (0, 1.3 - 0.32 * (2 - k) - 0.16, pl / 6 * (k + 1)), mats["laterite"])
    # walls with door + window openings
    wh = 2.75
    def wall_x(name, x0, x1, y, z0=pl, z1=pl + wh, t=0.22):
        box(name, (x1 - x0, t, z1 - z0), ((x0 + x1) / 2, y, (z0 + z1) / 2), mats["wall"])
    y = 3.5
    wall_x("fw1", -5.3, -3.1, y); wall_x("fw2", -1.9, -0.6, y); wall_x("fw3", 0.6, 1.9, y); wall_x("fw4", 3.1, 5.3, y)
    for (x0, x1) in ((-3.1, -1.9), (1.9, 3.1)):
        wall_x("fwlow", x0, x1, y, pl, pl + 0.9); wall_x("fwhigh", x0, x1, y, pl + 2.1, pl + wh)
    wall_x("fwdoor", -0.6, 0.6, y, pl + 2.15, pl + wh)
    box("bw", (10.6, 0.22, wh), (0, 10.0, pl + wh / 2), mats["wall"])
    box("lw", (0.22, 6.5, wh), (-5.3, 6.75, pl + wh / 2), mats["wall"])
    box("rw", (0.22, 6.5, wh), (5.3, 6.75, pl + wh / 2), mats["wall"])
    box("interior", (10.3, 6.2, wh - 0.05), (0, 6.8, pl + wh / 2), mats["dark"]).hide_render = True
    # door frame + leaves
    box("doorframeL", (0.1, 0.3, 2.15), (-0.6, y - 0.02, pl + 1.07), mats["wood"])
    box("doorframeR", (0.1, 0.3, 2.15), (0.6, y - 0.02, pl + 1.07), mats["wood"])
    box("doorframeT", (1.3, 0.3, 0.12), (0, y - 0.02, pl + 2.15), mats["wood"])
    box("threshold", (1.3, 0.3, 0.08), (0, y - 0.02, pl + 0.04), mats["wood"])
    for sx in (1, -1):
        hinge = empty(f"doorhinge{sx}", (sx * 0.55, y + 0.05, pl), None, rot=(0, 0, math.radians(sx * (-100 if door_open else 0))))
        box(f"doorleaf{sx}", (0.55, 0.06, 2.08), (-sx * 0.275, 0, 1.06), mats["wood"], hinge, bevel=0.01)
        for k in range(3):
            box(f"doorpanel{sx}{k}", (0.38, 0.08, 0.5), (-sx * 0.275, 0, 0.4 + k * 0.66), mats["woodlight"], hinge, bevel=0.02)
    # dim warm interior seen through the door
    box("darkroom", (2.5, 0.1, 2.6), (0, 5.5, pl + 1.3), mat("dimroom", "#2a1a10", 0.9))
    # windows with wooden bars
    for wx in (-2.5, 2.5):
        box(f"winframe{wx}", (1.3, 0.3, 1.3), (wx, y, pl + 1.5), mats["wood"]).display_type = 'WIRE'
        bpy.data.objects[f"winframe{wx}"].hide_render = True
        for (dx, dz, sx_, sz_) in ((0, 0.6, 1.3, 0.1), (0, -0.6, 1.3, 0.1), (-0.6, 0, 0.1, 1.3), (0.6, 0, 0.1, 1.3)):
            box(f"wf{wx}{dx}{dz}", (sx_, 0.28, sz_), (wx + dx, y - 0.03, pl + 1.5 + dz), mats["wood"])
        for k in range(6):
            cyl(f"wbar{wx}{k}", 0.022, 0.022, 1.15, (wx - 0.45 + k * 0.18, y - 0.03, pl + 1.5), mats["wood"])
        box(f"wdark{wx}", (1.2, 0.04, 1.2), (wx, y + 0.12, pl + 1.5), mat("dimroom", "#2a1a10", 0.9))
    # veranda pillars + low parapet seat (charupadi) on the sides
    for px in (-4.9, -2.6, 2.6, 4.9):
        cyl(f"pillar{px}", 0.11, 0.11, 2.6, (px, 1.5, pl + 1.3), mats["wood"], segs=16)
        cyl(f"pbase{px}", 0.17, 0.17, 0.12, (px, 1.5, pl + 0.06), mats["laterite"], segs=16)
        cyl(f"pcap{px}", 0.15, 0.13, 0.1, (px, 1.5, pl + 2.6), mats["wood"], segs=16)
    for (x0, x1) in ((-5.3, -2.75), (2.75, 5.3)):
        box(f"charupadi{x0}", (x1 - x0, 0.45, 0.06), ((x0 + x1) / 2, 1.45, pl + 0.45), mats["wood"])
        box(f"charupadib{x0}", (x1 - x0, 0.35, 0.42), ((x0 + x1) / 2, 1.45, pl + 0.21), mats["laterite"])
    box("beam", (11.0, 0.22, 0.2), (0, 1.5, pl + 2.68), mats["wood"])
    # hip roof (clay tiles) with a front gable (mukhappu)
    eave = pl + 2.75; ridge = eave + 2.7
    x0, x1, y0, y1 = -6.0, 6.0, 0.6, 10.9
    rx0, rx1, ry = -2.6, 2.6, (y0 + y1) / 2
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((x0, y0, eave), (x1, y0, eave), (x1, y1, eave), (x0, y1, eave), (rx0, ry, ridge), (rx1, ry, ridge))]
    for f in ((0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)):
        bm.faces.new([vs[i] for i in f])
    roof = _finish("roof", bm, mats["tile"], None, (0, 0, 0), (0, 0, 0), (1, 1, 1), smooth=False)
    roof.modifiers.new("sol", 'SOLIDIFY').thickness = 0.12
    box("ridge", (rx1 - rx0 + 0.2, 0.25, 0.18), (0, ry, ridge + 0.05), mats["tile"])
    # gable at front
    gx, gy, gz = 0, 2.2, eave + 0.95
    bm = bmesh.new()
    a = [bm.verts.new(v) for v in ((-1.6, gy, gz), (1.6, gy, gz), (0, gy, gz + 1.55))]
    bm.faces.new(a)
    gab = _finish("gable", bm, mats["woodlight"], None, (0, 0, 0), (0, 0, 0), (1, 1, 1), smooth=False)
    gab.modifiers.new("sol", 'SOLIDIFY').thickness = 0.05
    for sx in (1, -1):
        bm = bmesh.new()
        v = [bm.verts.new(p) for p in ((0, gy - 0.25, gz + 1.7), (sx * 1.85, gy - 0.25, gz - 0.15), (sx * 1.85, gy + 2.2, gz - 0.15 + 1.0), (0, gy + 2.2, gz + 1.7 + 0.3))]
        bm.faces.new(v)
        gr = _finish(f"gableroof{sx}", bm, mats["tile"], None, (0, 0, 0), (0, 0, 0), (1, 1, 1), smooth=False)
        gr.modifiers.new("sol", 'SOLIDIFY').thickness = 0.1
    for k in range(7):
        cyl(f"gablebar{k}", 0.02, 0.02, 1.2 - abs(k - 3) * 0.3, (-0.9 + k * 0.3, gy - 0.04, gz + 0.65 - abs(k - 3) * 0.15), mats["wood"])
    # fascia board
    box("fascia", (12.1, 0.06, 0.18), (0, y0 - 0.02, eave - 0.05), mats["wood"])
    H.update(door=Vector((0, 3.2, pl)), chair=Vector((-1.75, 2.45, pl)), steps=Vector((0, 0.4, 0)), floor=pl)
    return H


def courtyard(mats, with_grass=True):
    # big ground
    plane("ground", 160, 160, (0, 0, -0.01), mats["grass"])
    # sandy muttam in front of the house
    sand = loft("muttam", [(-0.02, 9, 7), (0.0, 9, 7)], mats["sand"], None, (0, -2.0, 0), seg=40, power=3.5)
    # laterite path out to the gate and beyond
    box("path", (1.7, 30, 0.02), (0, -21, 0.0), mats["path"])
    # low laterite compound wall with gate opening
    for (xa, xb) in ((-14, -1.2), (1.2, 14)):
        box(f"cwall{xa}", (xb - xa, 0.35, 0.9), ((xa + xb) / 2, -9.0, 0.45), mats["laterite"])
        box(f"cwallcap{xa}", (xb - xa, 0.42, 0.06), ((xa + xb) / 2, -9.0, 0.92), mats["wall"])
    for gx in (-1.2, 1.2):
        box(f"gatepost{gx}", (0.42, 0.42, 1.5), (gx, -9.0, 0.75), mats["laterite"])
        box(f"gatecap{gx}", (0.5, 0.5, 0.08), (gx, -9.0, 1.53), mats["wall"])
    for (xa, ya, yb) in ((-14, -9, 12), (14, -9, 12)):
        box(f"swall{xa}", (0.35, yb - ya, 0.9), (xa, (ya + yb) / 2, 0.45), mats["laterite"])
    # tulasi thara
    box("tulasi", (0.6, 0.6, 0.8), (3.2, -1.2, 0.4), mats["wall"], bevel=0.04)
    box("tulasi2", (0.7, 0.7, 0.08), (3.2, -1.2, 0.84), mats["laterite"])
    bush("tulasiplant", (3.2, -1.2, 0.85), 0.22, 5, mats)
    if with_grass:
        grass_field("grassL", (-30, -10, 0.0), (44, 60), 9000, mats, seed=2)
        grass_field("grassR", (30, -10, 0.0), (44, 60), 9000, mats, seed=3)
        grass_field("grassF", (0, -30, 0.0), (16, 40), 4000, mats, seed=4)


def palms_around(mats, positions, seed0=10):
    out = []
    for i, p in enumerate(positions):
        out.append(palm(f"palm{i}", p, seed=seed0 + i, mats=mats))
    return out


def exterior(mats, grass=True, vegetation=True):
    H = house(mats)
    courtyard(mats, grass)
    palms = []
    if vegetation:
        pos = [(-8, -4, 0), (-10.5, 2, 0), (-9, 8, 0), (8.5, -5, 0), (10.5, 3, 0), (9.5, 11, 0), (-4, 13, 0), (4, 14, 0),
               (-3.5, -12, 0), (4.5, -13, 0), (-7, -17, 0), (7, -19, 0), (-12, -11, 0), (13, -12, 0), (0, 18, 0),
               (-16, 6, 0), (17, 0, 0), (-20, -6, 0), (21, 9, 0), (-6, 22, 0), (9, 24, 0)]
        palms = palms_around(mats, pos)
        for i, p in enumerate([(-7, 0.5), (7.2, -0.5), (-6.8, 9.5), (6.8, 8), (-11, -6), (11.5, -8), (-2.6, -10.5), (2.8, -11.5)]):
            banana(f"banana{i}", (p[0], p[1], 0), 50 + i, mats)
        for i, p in enumerate([(-5.8, -0.8), (5.9, -1.5), (-2.4, -8.3), (2.5, -8.4), (-6, -8.3), (6.5, -8.2), (-12.5, 0), (12.5, 1),
                               (-1.8, -0.2), (1.9, 0.0)]):
            bush(f"bush{i}", (p[0], p[1], 0), 0.55 if i < 8 else 0.4, 70 + i, mats, flowers=(i % 2 == 0))
        # distant tree line
        for i in range(40):
            a = i / 40 * 2 * math.pi
            r_ = rnd.uniform(38, 55)
            x, y = math.cos(a) * r_, math.sin(a) * r_ + 10
            s = rnd.uniform(4, 8)
            sphere(f"far{i}", s, (x, y, s * 0.6), (1, 1, 0.9), mats["leafdark" if i % 2 else "leaf"], segs=14)
    return H, palms


def sway(palms, t, amp=1.0):
    for p in palms:
        ph = p["phase"]
        for k, fr in enumerate(p["fronds"]):
            fr.rotation_euler.x = math.radians(amp * 2.5 * math.sin(t * 1.3 + ph + k * 0.7))
            fr.rotation_euler.y = math.radians(amp * 3.0 * math.sin(t * 0.9 + ph + k * 1.3))
        p["crown"].rotation_euler.x = math.radians(amp * 1.2 * math.sin(t * 0.6 + ph))


# ------------------------------------------------------------------ interiors
def room(name, origin, size, mats, window=None, floor_m=None, wall_m=None):
    """open-front room: floor, back + side walls, ceiling. origin = floor centre."""
    ox, oy, oz = origin; W, D, Hh = size
    floor_m = floor_m or mats["redoxide"]; wall_m = wall_m or mats["wall"]
    box(f"{name}_floor", (W, D, 0.05), (ox, oy, oz - 0.025), floor_m)
    box(f"{name}_back", (W, 0.15, Hh), (ox, oy + D / 2, oz + Hh / 2), wall_m)
    box(f"{name}_ceil", (W, D, 0.08), (ox, oy, oz + Hh + 0.04), mats["woodlight"])
    for k in range(6):
        box(f"{name}_rafter{k}", (0.1, D, 0.12), (ox - W / 2 + W * (k + 0.5) / 6, oy, oz + Hh - 0.03), mats["wood"])
    # right wall solid, left wall with a window opening
    box(f"{name}_right", (0.15, D, Hh), (ox + W / 2, oy, oz + Hh / 2), wall_m)
    if window:
        wy, wz, ww, wh = window  # relative to room
        y0, y1 = oy - D / 2, oy + D / 2
        box(f"{name}_lw1", (0.15, (oy + wy - ww / 2) - y0, Hh), (ox - W / 2, (y0 + oy + wy - ww / 2) / 2, oz + Hh / 2), wall_m)
        box(f"{name}_lw2", (0.15, y1 - (oy + wy + ww / 2), Hh), (ox - W / 2, (y1 + oy + wy + ww / 2) / 2, oz + Hh / 2), wall_m)
        box(f"{name}_lw3", (0.15, ww, wz - wh / 2), (ox - W / 2, oy + wy, oz + (wz - wh / 2) / 2), wall_m)
        top0 = wz + wh / 2
        box(f"{name}_lw4", (0.15, ww, Hh - top0), (ox - W / 2, oy + wy, oz + (top0 + Hh) / 2), wall_m)
        for k in range(5):
            cyl(f"{name}_wbar{k}", 0.02, 0.02, wh, (ox - W / 2, oy + wy - ww / 2 + ww * (k + 0.5) / 5, oz + wz), mats["wood"])
        for (dy, dz, sy, sz) in ((0, wh / 2, ww + 0.1, 0.08), (0, -wh / 2, ww + 0.1, 0.08), (-ww / 2, 0, 0.08, wh), (ww / 2, 0, 0.08, wh)):
            box(f"{name}_wf{dy}{dz}", (0.2, sy, sz), (ox - W / 2, oy + wy + dy, oz + wz + dz), mats["wood"])
    else:
        box(f"{name}_left", (0.15, D, Hh), (ox - W / 2, oy, oz + Hh / 2), wall_m)


def kitchen(mats, origin=(-60, 0, 0)):
    ox, oy, oz = origin
    room("kit", origin, (5.0, 4.4, 2.9), mats, window=(0.4, 1.6, 1.1, 1.0),
         floor_m=mat("kitfloor", "#6a2116", rough=0.25, coat=0.4), wall_m=noise_mat("kitwall", "#d9c6a0", "#b9a079", scale=4, bump=0.2))
    # hearth (adupp) along back wall
    box("adupp", (2.2, 0.8, 0.75), (ox + 0.8, oy + 1.75, oz + 0.375), mats["clay"], bevel=0.04)
    for k, dx in enumerate((0.3, 1.25)):
        cyl(f"fire{k}", 0.17, 0.17, 0.02, (ox + dx, oy + 1.7, oz + 0.76), mat("ember", "#ff6a1a", emit="#ff5a10", emit_str=6.0), segs=20)
        pot = sphere(f"pot{k}", 0.2, (ox + dx, oy + 1.7, oz + 0.92), (1, 1, 0.85), mats["black"] if k == 0 else mats["brass"], segs=24)
    cyl("uruli", 0.25, 0.18, 0.1, (ox + 1.7, oy + 1.65, oz + 0.8), mats["brass"])
    # shelf with steel tumblers + jars
    box("shelf", (1.6, 0.3, 0.04), (ox - 1.2, oy + 2.05, oz + 1.6), mats["wood"])
    box("shelf2", (1.6, 0.3, 0.04), (ox - 1.2, oy + 2.05, oz + 2.1), mats["wood"])
    for k in range(5):
        cyl(f"tumbler{k}", 0.04, 0.035, 0.1, (ox - 1.8 + k * 0.28, oy + 2.0, oz + 1.67), mats["steel"])
    for k in range(4):
        cyl(f"jar{k}", 0.08, 0.08, 0.2, (ox - 1.7 + k * 0.33, oy + 2.0, oz + 2.22), mat(f"jarm{k}", ["#9a5a2a", "#c7a33a", "#7a3a1a", "#d9c07a"][k], 0.4))
    # brass vessels on floor, coconut scraper, banana bunch hanging
    cyl("kindi", 0.09, 0.06, 0.22, (ox + 2.0, oy + 0.9, oz + 0.11), mats["brass"])
    sphere("kindi_top", 0.07, (ox + 2.0, oy + 0.9, oz + 0.26), (1, 1, 0.7), mats["brass"])
    for k in range(3):
        cyl(f"pots_floor{k}", 0.15 - k * 0.02, 0.12, 0.25, (ox + 2.1 - k * 0.05, oy + 1.4 - k * 0.3, oz + 0.125), mats["clay"])
    # ceiling hanging lamp hook + rope with banana bunch
    cyl("rope", 0.01, 0.01, 0.6, (ox - 1.9, oy + 1.4, oz + 2.6), mats["woodlight"])
    for k in range(9):
        a = k * 0.7
        sphere(f"banana_f{k}", 0.05, (ox - 1.9 + math.cos(a) * 0.08, oy + 1.4 + math.sin(a) * 0.08, oz + 2.25 - k * 0.025), (0.6, 0.6, 1.8),
               mat("bananafruit", "#e6c13a", 0.5), segs=10)
    # low wooden seats (palaka/stools)
    box("stool_gma", (0.45, 0.4, 0.06), (ox - 0.25, oy + 0.2, oz + 0.33), mats["woodlight"], bevel=0.01)
    for sx in (1, -1):
        for sy in (1, -1):
            cyl(f"stl{sx}{sy}", 0.025, 0.025, 0.31, (ox - 0.25 + sx * 0.17, oy + 0.2 + sy * 0.15, oz + 0.155), mats["wood"])
    box("stool_kid", (0.38, 0.32, 0.05), (ox + 0.62, oy + 0.05, oz + 0.205), mats["woodlight"], bevel=0.01)
    for sx in (1, -1):
        for sy in (1, -1):
            cyl(f"stk{sx}{sy}", 0.022, 0.022, 0.19, (ox + 0.62 + sx * 0.14, oy + 0.05 + sy * 0.12, oz + 0.095), mats["wood"])
    return dict(gma_seat=Vector((ox - 0.25, oy + 0.2, oz + 0.36)), kid_seat=Vector((ox + 0.62, oy + 0.05, oz + 0.23)))


def bedroom(mats, origin=(60, 60, 0)):
    ox, oy, oz = origin
    room("bed", origin, (4.6, 4.2, 2.9), mats, window=(0.0, 1.55, 1.2, 1.1),
         floor_m=mat("bedfloor", "#6e2418", rough=0.22, coat=0.5), wall_m=noise_mat("bedwall", "#e3d3b2", "#c8b48e", scale=4, bump=0.15))
    # wooden cot (kattil)
    bx, by = ox - 0.4, oy + 0.7
    box("cot", (1.0, 2.0, 0.08), (bx, by, oz + 0.42), mats["wood"], bevel=0.01)
    for sx in (1, -1):
        for sy in (1, -1):
            cyl(f"cotleg{sx}{sy}", 0.04, 0.035, 0.42, (bx + sx * 0.45, by + sy * 0.95, oz + 0.21), mats["wood"])
    box("headboard", (1.05, 0.06, 0.55), (bx, by + 1.0, oz + 0.68), mats["wood"], bevel=0.015)
    box("mattress", (0.94, 1.94, 0.1), (bx, by, oz + 0.51), mat("mattress", "#ece3cf", 0.9, sheen=0.4), bevel=0.04)
    sphere("pillow", 0.2, (bx, by + 0.72, oz + 0.6), (1.6, 0.85, 0.35), mat("pillow", "#f5efe2", 0.85, sheen=0.6))
    # bedsheet (checked) blanket
    chk = noise_mat("checkered", "#c44b3a", "#f0e4cc", scale=16, wave=dict(type='BANDS', dir='X', dist=0), detail=0, bump=0)
    blanket = box("blanket", (0.98, 1.15, 0.07), (bx, by - 0.38, oz + 0.6), chk, bevel=0.03)
    # small wooden table with the lamp
    box("lamptable", (0.5, 0.45, 0.05), (bx + 0.95, by + 0.6, oz + 0.55), mats["wood"])
    for sx in (1, -1):
        for sy in (1, -1):
            cyl(f"tleg{sx}{sy}", 0.025, 0.025, 0.53, (bx + 0.95 + sx * 0.2, by + 0.6 + sy * 0.18, oz + 0.265), mats["wood"])
    lamp = nilavilakku("lamp", (bx + 0.95, by + 0.6, oz + 0.575), mats, scale=0.6)
    # wall shelf, calendar-like picture, photo frame placeholder handled per-shot
    box("wallshelf", (0.9, 0.2, 0.04), (ox + 1.2, oy + 2.0, oz + 1.65), mats["wood"])
    cyl("shelfpot", 0.07, 0.06, 0.16, (ox + 1.0, oy + 2.0, oz + 1.75), mats["brass"])
    box("trunkbox", (0.9, 0.5, 0.5), (ox + 1.4, oy + 1.5, oz + 0.25), mats["woodlight"], bevel=0.02)
    for k in range(3):
        box(f"trunkband{k}", (0.92, 0.52, 0.03), (ox + 1.4, oy + 1.5, oz + 0.12 + k * 0.15), mats["brass"])
    return dict(bed=Vector((bx, by, oz + 0.56)), lamp=lamp, blanket=blanket, origin=Vector(origin))


def lane(mats, origin=(120, 0, 0), grass=True):
    """village lane along Y with paddy field on +X side, palms, petti-kada shop at the far end"""
    ox, oy, oz = origin
    plane("lane_ground", 120, 120, (ox, oy, oz - 0.01), mats["grass"])
    box("lane_path", (1.9, 80, 0.02), (ox, oy, oz), mats["path"])
    # paddy field (lower, with water and bright rice tufts)
    paddy = plane("paddy_water", 40, 70, (ox + 22, oy, oz - 0.12), mats["water"])
    box("bund", (0.6, 70, 0.25), (ox + 1.6, oy, oz - 0.05), mats["grass"])
    if grass:
        pf = grass_field("paddy", (ox + 22, oy, oz - 0.1), (40, 70), 26000, mats, seed=7, h=0.35, color="rice_blade")
        grass_field("lanegrass", (ox - 14, oy, oz), (24, 70), 12000, mats, seed=8)
    pos = [(ox - 2.6, oy - 14), (ox - 3.2, oy - 6), (ox - 2.4, oy + 2), (ox - 3.5, oy + 10), (ox - 2.8, oy + 18), (ox - 6, oy - 2),
           (ox - 7, oy + 6), (ox - 6.5, oy - 10), (ox - 9, oy + 14), (ox + 3.0, oy - 20), (ox + 14, oy + 25), (ox + 22, oy + 30),
           (ox + 30, oy + 20), (ox - 4, oy - 24), (ox - 10, oy - 18), (ox - 3, oy + 26)]
    palms = [palm(f"lpalm{i}", (p[0], p[1], oz), seed=200 + i, mats=mats) for i, p in enumerate(pos)]
    for i in range(14):
        bush(f"lbush{i}", (ox - 1.7 - rnd.uniform(0, 1.5), oy - 25 + i * 3.6, oz), rnd.uniform(0.35, 0.6), 300 + i, mats, flowers=(i % 3 == 0))
    for i in range(5):
        banana(f"lban{i}", (ox - 4.5 - rnd.uniform(0, 2), oy - 18 + i * 8, oz), 400 + i, mats)
    # distant hills
    for i in range(10):
        sphere(f"hill{i}", rnd.uniform(18, 28), (ox + 40 + i * 4, oy + 70 + rnd.uniform(-10, 10), -8), (2.2, 1, 0.55),
               mat("hill", "#3d5a3a", 0.9), segs=16)
    for i in range(30):
        s = rnd.uniform(3, 6)
        sphere(f"lfar{i}", s, (ox - 20 + rnd.uniform(-5, 5), oy - 40 + i * 3, s * 0.6), (1, 1, 0.9), mats["leafdark"], segs=12)
    shop = petti_kada(mats, (ox - 2.2, oy - 16.0, oz), yaw=90)
    return dict(palms=palms, shop=shop)


def petti_kada(mats, loc, yaw=0):
    """small roadside wooden shop with glass sweet jars and a banana bunch"""
    root = empty("shop_root", loc, None, rot=(0, 0, math.radians(yaw)))
    w = mats["wood"]
    box("shop_body", (1.8, 1.2, 1.0), (0, 0.2, 0.5), mats["woodlight"], root, bevel=0.01)
    box("shop_counter", (1.9, 0.3, 0.05), (0, -0.45, 1.02), w, root)
    for sx in (1, -1):
        cyl(f"shop_post{sx}", 0.04, 0.04, 2.3, (sx * 0.9, -0.4, 1.15), w, root)
        cyl(f"shop_postb{sx}", 0.04, 0.04, 2.0, (sx * 0.9, 0.75, 1.0), w, root)
    box("shop_back", (1.8, 0.05, 1.2), (0, 0.78, 1.6), mats["woodlight"], root)
    roof = box("shop_roof", (2.4, 1.8, 0.04), (0, 0.15, 2.25), mat("tin", "#6f7f86", 0.4, metal=0.7), root, rot=(math.radians(-10), 0, 0))
    glass = mat("glass", "#dfeff0", rough=0.02, alpha=0.25)
    cols = ["#e8452b", "#f2c230", "#3aa65a", "#ec7fb0", "#7a4a2a"]
    for k in range(5):
        x = -0.75 + k * 0.37
        cyl(f"shop_jar{k}", 0.11, 0.11, 0.26, (x, -0.42, 1.18), glass, root)
        cyl(f"shop_sweets{k}", 0.1, 0.1, 0.16, (x, -0.42, 1.13), mat(f"sweet{k}", cols[k], 0.4, coat=0.8), root)
        cyl(f"shop_lid{k}", 0.115, 0.115, 0.03, (x, -0.42, 1.33), mat("lidred", "#b22", 0.4), root)
    # hanging banana bunch + snack packets strip
    for k in range(14):
        a = k * 0.9
        sphere(f"shop_ban{k}", 0.05, (0.65 + math.cos(a) * 0.12, -0.35 + math.sin(a) * 0.12, 1.9 - k * 0.03), (0.6, 0.6, 2.0),
               mat("bananafruit", "#e6c13a", 0.5), root, segs=10)
    for k in range(6):
        box(f"shop_pkt{k}", (0.12, 0.02, 0.18), (-0.8 + k * 0.15, -0.42, 2.0), mat(f"pkt{k}", ["#e63", "#36c", "#fc3", "#3a6", "#c3c", "#f63"][k], 0.4), root)
    # shelves inside with bottles
    for k in range(8):
        cyl(f"shop_bottle{k}", 0.04, 0.04, 0.22, (-0.7 + k * 0.2, 0.6, 1.55), mat(f"bot{k}", ["#e85", "#5a5", "#a3c", "#fd5"][k % 4], 0.2, coat=1), root)
    box("shop_bench", (1.2, 0.3, 0.05), (0, -1.1, 0.42), w, root)
    for sx in (1, -1):
        cyl(f"shop_benchleg{sx}", 0.03, 0.03, 0.42, (sx * 0.5, -1.1, 0.21), w, root)
    return root
