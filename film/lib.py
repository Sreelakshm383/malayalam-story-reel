"""Geometry, material and character helpers for the film (Blender 4.0, bpy).

Every character is built by ONE function (make_person) from a fixed spec, so
faces, hair, clothes, proportions and colours are identical in every shot.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

# ----------------------------------------------------------------- colours
def srgb(h, a=1.0):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, a)

_MATS = {}
def mat(name, color, rough=0.6, metal=0.0, sss=0.0, sss_col=None, emit=None, emit_str=0.0,
        spec=0.5, alpha=1.0, coat=0.0, sheen=0.0):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    col = srgb(color) if isinstance(color, str) else color
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
        b.inputs["Subsurface Scale"].default_value = 0.012
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = srgb(emit) if isinstance(emit, str) else emit
        b.inputs["Emission Strength"].default_value = emit_str
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = 'BLEND'
        m.shadow_method = 'HASHED'
    m.diffuse_color = col
    _MATS[name] = m
    return m


def noise_mat(name, c1, c2, scale=8.0, rough=0.8, bump=0.3, detail=6.0, wave=None, sss=0.0):
    detail = min(detail, 2.0); bump = bump if name in ("tile", "trunk", "rice") else 0.0
    """two-colour procedural material (ground, wood, walls, tiles...)"""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
    tc = N.new("ShaderNodeTexCoord")
    if wave:
        tex = N.new("ShaderNodeTexWave"); tex.wave_type = wave.get("type", 'BANDS')
        tex.bands_direction = wave.get("dir", 'X')
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Distortion"].default_value = wave.get("dist", 4.0)
        tex.inputs["Detail"].default_value = detail
        L.new(tc.outputs["Object"], tex.inputs["Vector"])
    else:
        tex = N.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = detail
        L.new(tc.outputs["Object"], tex.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = srgb(c1); ramp.color_ramp.elements[1].color = srgb(c2)
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.75
    L.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    if bump:
        bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump
        bm.inputs["Distance"].default_value = 0.02
        L.new(tex.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = srgb(c1)
    _MATS[name] = m
    return m


def image_mat(name, path, rough=0.5, faded=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    img = N.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(path)
    col = img.outputs["Color"]
    if faded:
        mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
        mix.inputs[0].default_value = faded
        mix.inputs[7].default_value = srgb("#c9a774")
        L.new(col, mix.inputs[6]); col = mix.outputs[2]
    L.new(col, b.inputs["Base Color"])
    if emit:
        L.new(col, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = emit
    return m


# ----------------------------------------------------------------- objects
COLL = None
def link(ob):
    (COLL or bpy.context.scene.collection).objects.link(ob)
    return ob


def _finish(name, bm, m, parent, loc, rot, scale, smooth=True, subsurf=0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if m is not None:
        me.materials.append(m)
    link(ob)
    if parent is not None:
        ob.parent = parent
    ob.location = loc; ob.rotation_euler = rot; ob.scale = scale
    if subsurf:
        md = ob.modifiers.new("ss", 'SUBSURF'); md.levels = subsurf; md.render_levels = subsurf
    return ob


def sphere(name, r, loc=(0, 0, 0), scale=(1, 1, 1), m=None, parent=None, rot=(0, 0, 0), segs=32, rings=None, cut=None, plane_cut=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings or segs // 2, radius=r)
    if plane_cut:
        co, no = plane_cut
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_inner=True)
    if cut:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if cut(v.co)], context='VERTS')
    return _finish(name, bm, m, parent, loc, rot, scale)


def cyl(name, r1, r2, depth, loc=(0, 0, 0), m=None, parent=None, rot=(0, 0, 0), scale=(1, 1, 1), segs=24, caps=True, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    ob = _finish(name, bm, m, parent, loc, rot, scale, smooth)
    if caps and smooth:
        ob.data.use_auto_smooth = True if hasattr(ob.data, "use_auto_smooth") else None
    return ob


def box(name, size, loc=(0, 0, 0), m=None, parent=None, rot=(0, 0, 0), bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    ob = _finish(name, bm, m, parent, loc, rot, (1, 1, 1), smooth=False)
    if bevel:
        md = ob.modifiers.new("bv", 'BEVEL'); md.width = bevel; md.segments = 2
    return ob


def torus(name, R, r, loc=(0, 0, 0), m=None, parent=None, rot=(0, 0, 0), scale=(1, 1, 1), seg=32, mseg=10):
    bm = bmesh.new()
    verts = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(mseg):
            b = 2 * math.pi * j / mseg
            x = (R + r * math.cos(b)) * math.cos(a); y = (R + r * math.cos(b)) * math.sin(a); z = r * math.sin(b)
            ring.append(bm.verts.new((x, y, z)))
        verts.append(ring)
    for i in range(seg):
        for j in range(mseg):
            a, b = verts[i][j], verts[(i + 1) % seg][j]
            c, d = verts[(i + 1) % seg][(j + 1) % mseg], verts[i][(j + 1) % mseg]
            bm.faces.new((a, b, c, d))
    return _finish(name, bm, m, parent, loc, rot, scale)


def tube(name, pts, r, m=None, parent=None, mseg=8, r_end=None):
    """polyline tube through points (list of Vector), radius tapering to r_end"""
    bm = bmesh.new()
    pts = [Vector(p) for p in pts]
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized(); v = t.cross(u).normalized()
        rr = r if r_end is None else r + (r_end - r) * i / (n - 1)
        rings.append([bm.verts.new(p + rr * (math.cos(2 * math.pi * k / mseg) * u + math.sin(2 * math.pi * k / mseg) * v)) for k in range(mseg)])
    for i in range(n - 1):
        for k in range(mseg):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % mseg], rings[i][(k + 1) % mseg]))
    return _finish(name, bm, m, parent, (0, 0, 0), (0, 0, 0), (1, 1, 1))


def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    link(ob)
    if parent is not None:
        ob.parent = parent
    ob.location = loc; ob.rotation_euler = rot
    return ob


def plane(name, sx, sy, loc=(0, 0, 0), m=None, parent=None, rot=(0, 0, 0), subdiv=0):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=max(1, subdiv), y_segments=max(1, subdiv), size=0.5)
    bmesh.ops.scale(bm, vec=(sx, sy, 1), verts=bm.verts)
    return _finish(name, bm, m, parent, loc, rot, (1, 1, 1), smooth=False)


def loft(name, profile, m=None, parent=None, loc=(0, 0, 0), seg=32, power=2.4, cap=True, rot=(0, 0, 0), yoff=None):
    """smooth body from rings: profile=[(z, rx, ry), ...] bottom->top, superellipse cross-section"""
    bm = bmesh.new(); rings = []
    for (z, rx, ry) in profile:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            c, s_ = math.cos(a), math.sin(a)
            x = rx * math.copysign(abs(c) ** (2 / power), c)
            y = ry * math.copysign(abs(s_) ** (2 / power), s_)
            ring.append(bm.verts.new((x, y + (yoff(z) if yoff else 0), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(seg):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k]))
    if cap:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    ob = _finish(name, bm, m, parent, loc, rot, (1, 1, 1))
    md = ob.modifiers.new("ss", 'SUBSURF'); md.levels = 1; md.render_levels = 2
    return ob


def clumps(name, R, dirs, m, parent, size=0.34, dist=0.8, flat=0.55, stretch=1.25, center=(0, 0, 0)):
    """stylised chunky hair: ellipsoid clumps on the skull surface pointing along dirs"""
    obs = []
    for i, dv in enumerate(dirs):
        v = Vector(dv).normalized()
        q = v.to_track_quat('Z', 'Y')
        ob = sphere(f"{name}{i}", R * size, tuple(Vector(center) + v * R * dist), (stretch, 1.0, flat), m, parent, segs=20)
        ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = q
        obs.append(ob)
    return obs


def hemi_dirs(n, zmin, seed, front_block=None):
    rnd = random.Random(seed); out = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n * 3):
        z = 1 - (i / (n * 3 - 1)) * 2
        r = math.sqrt(max(0, 1 - z * z)); th = golden * i
        x, y = math.cos(th) * r, math.sin(th) * r
        if z < zmin:
            continue
        if front_block and front_block(x, y, z):
            continue
        out.append((x + rnd.uniform(-.05, .05), y, z))
    return out


# ----------------------------------------------------------------- characters
SPECS = {
    # Little child (boy, 6): yellow kurta with orange collar trim, teal shorts
    "child": dict(H=1.12, headR=0.135, head_scale=(1.0, 0.97, 0.98), neck=0.035,
                  torso=(0.14, 0.10, 0.17), legs=0.43, arm=(0.17, 0.16), limb_r=0.047,
                  skin="#b9805a", hair="#17110d", hair_style="kid", eye=0.30,
                  top="#f2b632", trim="#e0642b", bottom="#1f8a86", clothes="kid", iris="#3b2414"),
    # Grandmother: off-white kasavu set-saree with gold border, maroon blouse, grey bun
    "grandma": dict(H=1.55, headR=0.125, head_scale=(0.98, 0.96, 1.04), neck=0.05,
                    torso=(0.19, 0.14, 0.27), legs=0.70, arm=(0.26, 0.24), limb_r=0.053,
                    skin="#a8714c", hair="#8f8a83", hair_style="bun", eye=0.25,
                    top="#7c1d2b", trim="#d4a437", bottom="#f3ecd9", clothes="saree", iris="#2e1c10"),
    # Grandfather: cream shirt, white kasavu mundu, grey side hair, moustache, round glasses
    "grandpa": dict(H=1.68, headR=0.128, head_scale=(0.97, 0.97, 1.06), neck=0.06,
                    torso=(0.19, 0.13, 0.30), legs=0.78, arm=(0.28, 0.26), limb_r=0.052,
                    skin="#9b6646", hair="#a19c94", hair_style="balding", eye=0.24,
                    top="#efe6cf", trim="#d4a437", bottom="#f7f3ea", clothes="mundu", iris="#2e1c10"),
    # The same child, grown up: same face colours/hair, yellow kurta + teal-grey trousers
    "adult": dict(H=1.72, headR=0.122, head_scale=(0.96, 0.97, 1.08), neck=0.07,
                  torso=(0.18, 0.12, 0.31), legs=0.82, arm=(0.29, 0.27), limb_r=0.052,
                  skin="#b07a55", hair="#17110d", hair_style="adult", eye=0.24,
                  top="#e7aa2e", trim="#e0642b", bottom="#2f5f63", clothes="adult", iris="#3b2414"),
}


class Person:
    pass


def make_person(key, name=None):
    s = SPECS[key]; name = name or key
    P = Person(); P.key = key; P.spec = s
    R = s["headR"]
    skin = mat(f"skin_{key}", s["skin"], rough=0.45, sss=0.25)
    cheek = mat(f"cheek_{key}", s["skin"], rough=0.45, sss=0.3)
    top = mat(f"top_{key}", s["top"], rough=0.8, sheen=0.4)
    trim = mat(f"trim_{key}", s["trim"], rough=0.35, metal=0.6 if s["trim"] == "#d4a437" else 0.0)
    bottom = mat(f"bottom_{key}", s["bottom"], rough=0.8, sheen=0.4)
    hc = s["hair"].lstrip("#"); dk = "#" + "".join(f"{int(int(hc[i:i+2], 16) * 0.6):02x}" for i in (0, 2, 4))
    hc = s["hair"].lstrip("#"); dk = "#" + "".join(f"{int(int(hc[i:i+2], 16) * 0.78):02x}" for i in (0, 2, 4))
    hair = noise_mat(f"hair_{key}", s["hair"], dk, scale=160, rough=0.45, wave=dict(type='BANDS', dir='Y', dist=1.5), detail=2)
    white = mat("eyewhite", "#f4f1ea", rough=0.15, coat=0.5)
    iris = mat(f"iris_{key}", s["iris"], rough=0.1, coat=1.0)
    pupil = mat("pupil", "#050302", rough=0.05, coat=1.0)
    mouth_m = mat("mouthin", "#3a0f0c", rough=0.6)
    lip = mat(f"lip_{key}", "#7a3b2e", rough=0.4)
    brow_m = mat(f"brow_{key}", s["hair"] if key != "child" and key != "adult" else "#120c08", rough=0.8)

    legs = s["legs"]; tw, td, th = s["torso"]
    hipZ = legs + 0.04
    shZ = hipZ + th * 1.55
    headZ = shZ + s["neck"] + R * 1.0

    P.root = empty(f"{name}_root")
    P.hips = empty(f"{name}_hips", (0, 0, hipZ), P.root)
    P.chest = empty(f"{name}_chest", (0, 0, 0.02), P.hips)          # spine bend pivot
    # torso
    belly = 1.06 if key == "grandpa" else (1.04 if key == "grandma" else 1.0)
    hem = -0.42 * th if s["clothes"] in ("kid", "adult") else 0.0
    loft(f"{name}_torso", [(hem, 1.0 * tw, 0.98 * td), (0.05 * th, 0.97 * tw * belly, 0.97 * td * belly),
                           (0.45 * th, 0.93 * tw * belly, 0.95 * td * belly), (0.95 * th, 1.0 * tw, 1.0 * td),
                           (1.30 * th, 0.98 * tw, 0.88 * td), (1.48 * th, 0.72 * tw, 0.66 * td),
                           (1.58 * th, 0.32 * tw, 0.34 * td)], top, P.chest)
    if s["clothes"] == "kid":
        cyl(f"{name}_collar", tw * 0.42, tw * 0.38, 0.03, (0, -td * 0.25, th * 1.45), trim, P.chest, rot=(math.radians(-15), 0, 0))
        box(f"{name}_placket", (0.03, 0.01, th * 0.55), (0, -td * 0.98, th * 1.05), trim, P.chest)
        loft(f"{name}_shorts", [(-0.12, 0.98 * tw, 0.95 * td), (-0.02, 0.99 * tw, 0.99 * td), (0.04, 0.97 * tw, 0.97 * td)], bottom, P.hips)
    if s["clothes"] == "adult":
        box(f"{name}_placket", (0.03, 0.01, th * 0.75), (0, -td * 0.97, th * 0.85), trim, P.chest)
        cyl(f"{name}_collar", tw * 0.36, tw * 0.33, 0.035, (0, -td * 0.15, th * 1.5), trim, P.chest, rot=(math.radians(-12), 0, 0))
        loft(f"{name}_pelvis", [(-0.12, 0.93 * tw, 0.95 * td), (-0.02, 0.95 * tw, 0.97 * td), (0.06, 0.95 * tw, 0.96 * td)], bottom, P.hips)
    if s["clothes"] == "mundu":
        # shirt pocket + buttons
        box(f"{name}_pocket", (0.07, 0.01, 0.07), (-tw * 0.45, -td * 0.88, th * 1.05), top, P.chest)
        for k in range(4):
            sphere(f"{name}_btn{k}", 0.008, (0, -td * 0.99, th * (1.35 - k * 0.22)), (1, 0.5, 1), mat("btn", "#d9d2c0", 0.3), P.chest)
        cyl(f"{name}_collar", tw * 0.40, tw * 0.36, 0.035, (0, -td * 0.1, th * 1.5), top, P.chest, rot=(math.radians(-12), 0, 0))
        # mundu: long wrap from waist to ankle with gold kasavu border + front fold
        L = hipZ - 0.07
        loft(f"{name}_mundu", [(-L, 1.10 * tw, 1.05 * td * 1.15), (-L * 0.5, 1.08 * tw, 1.06 * td * 1.15), (-0.1, 1.06 * tw, 1.1 * td * 1.1),
                               (0.03, 1.02 * tw, 1.02 * td), (0.07, 1.0 * tw, 0.98 * td)], bottom, P.hips)
        loft(f"{name}_kasavu", [(-L + 0.035, 1.112 * tw, 1.062 * td * 1.15), (-L + 0.075, 1.112 * tw, 1.062 * td * 1.15)], trim, P.hips, cap=False)
        box(f"{name}_fold", (0.05, 0.02, hipZ - 0.1), (0.05, -td * 1.2, -(hipZ - 0.06) / 2 + 0.0), bottom, P.hips, rot=(0, 0, 0.2))
    if s["clothes"] == "saree":
        skirt_h = hipZ - 0.03
        loft(f"{name}_skirt", [(-skirt_h + 0.03, 1.32 * tw, 1.25 * td), (-skirt_h * 0.6, 1.2 * tw, 1.18 * td), (-skirt_h * 0.25, 1.16 * tw, 1.16 * td),
                               (-0.02, 1.08 * tw, 1.08 * td), (0.08, 0.97 * tw, 0.98 * td)], bottom, P.hips)
        loft(f"{name}_kasavu", [(-skirt_h + 0.05, 1.33 * tw, 1.262 * td), (-skirt_h + 0.11, 1.325 * tw, 1.258 * td)], trim, P.hips, cap=False)
        # pleats in front
        for k in range(5):
            box(f"{name}_pleat{k}", (0.018, 0.02, skirt_h * 0.85), (-0.04 + k * 0.02, -td * 1.17, -skirt_h * 0.48), bottom, P.hips, rot=(math.radians(-8), 0, 0))
        loft(f"{name}_wrap", [(-0.02, 1.0 * tw * 1.06, 0.99 * td * 1.06), (0.3 * th, 0.95 * tw * 1.06, 0.97 * td * 1.06),
                              (0.62 * th, 0.94 * tw * 1.05, 0.97 * td * 1.05)], bottom, P.chest)
        # blouse is the torso material (maroon) -> saree pallu drapes diagonally across the chest
        pallu = torus(f"{name}_pallu", 1.0, 0.24, (0.0, 0, th * 0.85), bottom, P.chest,
                      rot=(0, math.radians(38), 0), scale=(tw * 1.02, td * 1.08, th * 0.9))
        torus(f"{name}_pallu_edge", 1.0, 0.045, (0.0, 0, th * 0.85 - 0.0), trim, P.chest,
              rot=(0, math.radians(38), 0), scale=(tw * 1.16, td * 1.2, th * 1.05))
        box(f"{name}_pallu_back", (0.16, 0.02, 0.55), (-tw * 0.55, td * 0.95, th * 0.45), bottom, P.chest, rot=(math.radians(6), 0, 0))
        box(f"{name}_pallu_back_edge", (0.16, 0.021, 0.04), (-tw * 0.55, td * 0.95, th * 0.45 - 0.26), trim, P.chest, rot=(math.radians(6), 0, 0))
    # neck & head
    P.neck = empty(f"{name}_neckj", (0, 0, th * 1.55 - 0.02), P.chest)
    cyl(f"{name}_neck", R * 0.38, R * 0.42, s["neck"] + 0.06, (0, 0, s["neck"] / 2), skin, P.neck)
    P.head = empty(f"{name}_head", (0, 0, s["neck"] + R * 0.95), P.neck)
    hs = s["head_scale"]
    sphere(f"{name}_skull", R, (0, 0, 0), hs, skin, P.head)
    if key != "child":
        sphere(f"{name}_jaw", R * 0.68, (0, -R * 0.28, -R * 0.42), (1.0, 0.95, 0.85), skin, P.head)
    sphere(f"{name}_cheekL", R * 0.26, (R * 0.46, -R * 0.66, -R * 0.26), (1, 0.8, 0.9), cheek, P.head)
    sphere(f"{name}_cheekR", R * 0.26, (-R * 0.46, -R * 0.66, -R * 0.26), (1, 0.8, 0.9), cheek, P.head)
    sphere(f"{name}_nose", R * 0.13, (0, -R * 0.98, -R * 0.12), (0.95, 0.9, 1.1), skin, P.head)
    for side, sx in (("L", 1), ("R", -1)):
        sphere(f"{name}_ear{side}", R * 0.2, (sx * R * 0.97, 0.0, -R * 0.08), (0.45, 0.8, 1.2), skin, P.head)
    # eyes
    e = R * s["eye"]
    P.eyes, P.lids, P.brows = [], [], []
    for side, sx in (("L", 1), ("R", -1)):
        ec = empty(f"{name}_eyec{side}", (sx * R * 0.32, -R * 0.71, R * 0.08), P.head)
        sphere(f"{name}_eyew{side}", e, (0, 0, 0), (1, 1, 1), white, ec, segs=24)
        gaze = empty(f"{name}_gaze{side}", (0, 0, 0), ec)
        sphere(f"{name}_iris{side}", e * 0.58, (0, -e * 0.86, 0), (1, 0.35, 1), iris, gaze, segs=24)
        sphere(f"{name}_pupil{side}", e * 0.3, (0, -e * 0.99, 0), (1, 0.3, 1), pupil, gaze, segs=16)
        sphere(f"{name}_glint{side}", e * 0.09, (sx * -e * 0.18, -e * 1.02, e * 0.2), (1, 0.4, 1),
               mat("glint", "#ffffff", emit="#ffffff", emit_str=3.0), gaze, segs=8)
        lid = sphere(f"{name}_lid{side}", e * 1.07, (0, 0, 0), (1, 1, 1), skin, ec, segs=24, cut=lambda c: c.z < -0.001)
        lid.rotation_euler.x = math.radians(-32)
        bpts = []
        for k in range(5):
            bx_ = 0.18 + 0.30 * k / 4; bz_ = 0.34 + 0.07 * math.sin(math.pi * (k + 0.6) / 5)
            by_ = -math.sqrt(max(0.05, 1 - (bx_ / hs[0]) ** 2 - (bz_ / hs[2]) ** 2)) * hs[1] - 0.015
            bpts.append((sx * R * bx_, R * by_, R * bz_))
        brow = tube(f"{name}_brow{side}", bpts, R * (0.045 if key in ("child", "adult") else 0.035), brow_m, None, r_end=R * 0.02)
        brow.parent = P.head
        brow_base = brow.location.z
        P.eyes.append(gaze); P.lids.append(lid); P.brows.append(brow)
    # mouth: dark interior that opens with speech + smile line
    P.mouth = sphere(f"{name}_mouth", 1, (0, -R * 0.84, -R * 0.43), (R * 0.22, R * 0.06, R * 0.012), mouth_m, P.head,
                     rot=(math.radians(-15), 0, 0))
    pts = []
    for k in range(9):
        x = -R * 0.24 + R * 0.48 * k / 8
        z = -R * 0.43 + 1.2 * (x / R) ** 2 * R * 0.9
        y = -math.sqrt(max(0.05, 1 - (x / R / hs[0]) ** 2 - (z / R / hs[2]) ** 2)) * hs[1] * R - R * 0.012
        pts.append((x, y, z))
    P.smile = tube(f"{name}_smile", pts, R * 0.022, lip, P.head, r_end=None)
    # hair
    hs_ = s["hair_style"]
    def cap_cut(front_z, back_z, top_cut=None):
        def f(c):
            back = (c.y / R + 1) / 2   # 0 front .. 1 back
            zlim = front_z + (back_z - front_z) * back
            if top_cut is not None and c.z > top_cut and c.y < R * 0.6:
                return True
            return c.z < zlim * R
        return f
    def hairline(front, back, r):
        c2 = (back - front) / 2.0; c1 = (front + back) / 2.0 * r
        return ((0, 0, c1), Vector((0, -c2, 1)).normalized())
    face_blk = lambda x, y, z: (y < -0.2 and z < 0.6) or (y < 0.25 and z < 0.15)
    if hs_ == "kid":
        sphere(f"{name}_hair", R * 1.02, (0, 0.01, 0.02), hs, hair, P.head, plane_cut=hairline(0.32, -0.55, R * 1.02), segs=48)
        clumps(f"{name}_hc", R, hemi_dirs(26, -0.35, 7, face_blk), hair, P.head, size=0.36, dist=0.78, flat=0.6)
        # fringe sweeping to one side
        for k in range(5):
            x = -0.45 + k * 0.22
            ob = sphere(f"{name}_fringe{k}", R * 0.24, (x * R, -R * 0.78, R * (0.52 - 0.03 * abs(x) * 2)), (1.5, 0.7, 0.75), hair, P.head,
                        rot=(math.radians(25), math.radians(-25), math.radians(15)))
        sphere(f"{name}_tuft", R * 0.2, (0.05 * R, 0.1 * R, R * 1.05), (0.6, 1.4, 0.55), hair, P.head, rot=(0.9, 0.2, 0.3))
    if hs_ == "adult":
        sphere(f"{name}_hair", R * 1.02, (0, 0.01, 0.03), hs, hair, P.head, plane_cut=hairline(0.42, -0.45, R * 1.02), segs=48)
        clumps(f"{name}_hc", R, hemi_dirs(24, -0.25, 9, face_blk), hair, P.head, size=0.34, dist=0.8, flat=0.5)
        for k in range(4):
            x = -0.35 + k * 0.22
            sphere(f"{name}_quiff{k}", R * 0.26, (x * R, -R * 0.66, R * 0.72), (1.4, 0.9, 0.7), hair, P.head,
                   rot=(math.radians(40), math.radians(-20), math.radians(10)))
        sphere(f"{name}_beard", R * 0.67, (0, -R * 0.29, -R * 0.45), (1.03, 0.97, 0.86), mat("stubble", "#4a2f20", 0.9), P.head,
               cut=lambda c: c.z > -0.12 * R or (c.y > 0.15 * R))
    if hs_ == "bun":
        sphere(f"{name}_hair", R * 1.04, (0, 0.01, 0.02), hs, hair, P.head, plane_cut=hairline(0.36, -0.5, R * 1.04), segs=48)
        sphere(f"{name}_bun", R * 0.42, (0, R * 0.92, R * 0.15), (1, 0.85, 1), hair, P.head)
        box(f"{name}_part", (0.006, R * 0.9, 0.004), (0, -R * 0.3, R * 1.06), mat("part", "#8a7d70"), P.head, rot=(0.35, 0, 0))
        sphere(f"{name}_bindi", R * 0.035, (0, -R * 0.99, R * 0.3), (1, 0.4, 1), mat("bindi", "#a3121d", 0.3), P.head)
        for sx in (1, -1):
            sphere(f"{name}_earring{sx}", R * 0.05, (sx * R * 1.0, -R * 0.05, -R * 0.3), (1, 1, 1), mat("gold", "#d4a437", 0.25, metal=1.0), P.head)
    if hs_ == "balding":
        sphere(f"{name}_hair", R * 1.03, (0, 0.01, 0.0), hs, hair, P.head, cut=cap_cut(0.2, -0.5, top_cut=R * 0.42))
        clumps(f"{name}_hc", R, [d_ for d_ in hemi_dirs(30, -0.45, 3) if d_[2] < 0.45 and d_[1] > -0.45], hair, P.head,
               size=0.26, dist=0.86, flat=0.4)
        sphere(f"{name}_moust", R * 0.2, (0, -R * 0.95, -R * 0.29), (1.6, 0.5, 0.45), hair, P.head, rot=(math.radians(-10), 0, 0))
        gm = mat("glassframe", "#3a2a1c", 0.3, metal=0.4)
        for sx in (1, -1):
            torus(f"{name}_glass{sx}", R * 0.27, R * 0.018, (sx * R * 0.34, -R * 1.02, R * 0.08), gm, P.head, rot=(math.radians(90), 0, 0))
            cyl(f"{name}_temple{sx}", R * 0.014, R * 0.014, R * 0.9, (sx * R * 0.62, -R * 0.55, R * 0.12), gm, P.head, rot=(math.radians(90), 0, 0))
        cyl(f"{name}_bridge", R * 0.014, R * 0.014, R * 0.15, (0, -R * 1.0, R * 0.12), gm, P.head, rot=(0, math.radians(90), 0))
        sphere(f"{name}_lens", 1, (0, 0, 0), (1, 1, 1), None, P.head).hide_render = True
        # wrinkle hint: forehead lines
        for k in range(2):
            torus(f"{name}_wrinkle{k}", R * 0.95, R * 0.008, (0, R * 0.12, R * (0.52 + k * 0.09)),
                  mat("wrinkle", "#7d4f35", 0.7), P.head, rot=(math.radians(-8), 0, 0), scale=(0.45, 1.25, 1), seg=24, mseg=6).hide_render = False
    if key == "grandma":
        for k in range(1):
            torus(f"{name}_wrinkle{k}", R * 0.95, R * 0.007, (0, R * 0.12, R * 0.58),
                  mat("wrinkle_g", "#7f5138", 0.7), P.head, rot=(math.radians(-8), 0, 0), scale=(0.4, 1.25, 1), seg=24, mseg=6)
    # arms
    a1, a2 = s["arm"]; lr = s["limb_r"]
    P.sh, P.el, P.hand = [], [], []
    sleeve_len = {"kid": 0.55, "saree": 0.4, "mundu": 0.55, "adult": 1.0}[s["clothes"]]
    for side, sx in (("L", 1), ("R", -1)):
        sh = empty(f"{name}_sh{side}", (sx * (tw * 0.86), 0, th * 1.34), P.chest)
        sphere(f"{name}_shball{side}", lr * 1.08, (0, 0, 0), (1, 1, 1), top, sh)
        cyl(f"{name}_upper{side}", lr, lr * 0.9, a1, (0, 0, -a1 / 2), skin, sh)
        cyl(f"{name}_sleeve{side}", lr * 1.12, lr * 1.12, a1 * sleeve_len, (0, 0, -a1 * sleeve_len / 2), top, sh)
        if s["clothes"] == "kid" or s["clothes"] == "saree":
            cyl(f"{name}_cuff{side}", lr * 1.14, lr * 1.14, 0.015, (0, 0, -a1 * sleeve_len), trim, sh, caps=False)
        el = empty(f"{name}_el{side}", (0, 0, -a1), sh)
        sphere(f"{name}_elball{side}", lr * 0.92, (0, 0, 0), (1, 1, 1), top if sleeve_len >= 1 else skin, el)
        cyl(f"{name}_fore{side}", lr * 0.9, lr * 0.75, a2, (0, 0, -a2 / 2), top if sleeve_len >= 1 else skin, el)
        hd = empty(f"{name}_hand{side}", (0, 0, -a2), el)
        sphere(f"{name}_palm{side}", lr * 1.35, (0, 0, -lr * 1.0), (0.75, 1.0, 1.15), skin, hd)
        sphere(f"{name}_thumb{side}", lr * 0.45, (sx * -lr * 0.15, -lr * 0.9, -lr * 0.5), (1, 1, 1.6), skin, hd, rot=(0.4, 0, 0))
        if key == "grandma":
            torus(f"{name}_bangle{side}", lr * 0.95, lr * 0.12, (0, 0, -a2 * 0.92), mat("gold", "#d4a437", 0.25, metal=1.0), el)
        P.sh.append(sh); P.el.append(el); P.hand.append(hd)
    # legs
    P.hip, P.knee, P.foot = [], [], []
    l1 = legs * 0.5; l2 = legs * 0.5
    for side, sx in (("L", 1), ("R", -1)):
        hp = empty(f"{name}_hip{side}", (sx * tw * 0.45, 0, -0.02), P.hips)
        lm = bottom if s["clothes"] in ("adult",) else skin
        cyl(f"{name}_thigh{side}", lr * 1.3, lr * 1.05, l1, (0, 0, -l1 / 2), lm, hp)
        if s["clothes"] == "kid":
            cyl(f"{name}_shortleg{side}", lr * 1.65, lr * 1.55, l1 * 0.55, (0, 0, -l1 * 0.22), bottom, hp)
        kn = empty(f"{name}_knee{side}", (0, 0, -l1), hp)
        sphere(f"{name}_kneeb{side}", lr * 1.05, (0, 0, 0), (1, 1, 1), lm, kn)
        cyl(f"{name}_shin{side}", lr * 1.05, lr * 0.8, l2, (0, 0, -l2 / 2), lm, kn)
        ft = empty(f"{name}_foot{side}", (0, 0, -l2), kn)
        fm = skin if key != "adult" else mat("sandal", "#4a2e1d", 0.6)
        sphere(f"{name}_footm{side}", lr * 1.2, (0, -lr * 0.9, -0.02), (0.85, 1.8, 0.55), fm, ft)
        if key != "child":
            box(f"{name}_chappal{side}", (lr * 2.0, lr * 4.2, 0.012), (0, -lr * 0.9, -0.045), mat("chappal", "#5b3a24", 0.7), ft)
        P.hip.append(hp); P.knee.append(kn); P.foot.append(ft)
    P.a1 = a1; P.a2 = a2
    P.hipZ = hipZ; P.R = R; P.l1 = l1; P.l2 = l2; P.lr = lr
    P.stand_skirt = [o for o in bpy.data.objects if o.name.startswith(name + "_") and any(k in o.name for k in ("_skirt", "_mundu", "_kasavu", "_pleat", "_fold"))]
    P.sit_skirt = []
    if s["clothes"] in ("saree", "mundu"):
        cm = bottom
        k_ = 1.12 if s["clothes"] == "saree" else 1.05
        lap = loft(f"{name}_lap", [(-0.12, tw * k_, lr * 1.7), (l1 * 0.5, tw * k_ * 1.0, lr * 1.65), (l1 + lr * 1.2, tw * k_ * 1.0, lr * 1.5),
                                   (l1 + lr * 1.6, tw * k_ * 0.95, lr * 1.0)], cm, P.hips, loc=(0, 0.02, -0.03), rot=(math.radians(90), 0, 0))
        drop = loft(f"{name}_drop", [(-(l2 + 0.03), tw * k_ * 1.08, lr * 2.4), (-l2 * 0.5, tw * k_ * 1.04, lr * 2.0), (0.0, tw * k_ * 1.0, lr * 1.6)],
                    cm, P.hips, loc=(0, -l1 - lr * 0.2, -0.04))
        band = loft(f"{name}_dropband", [(-(l2 - 0.01), tw * k_ * 1.085, lr * 2.42), (-(l2 - 0.06), tw * k_ * 1.08, lr * 2.38)], trim, P.hips,
                    loc=(0, -l1 - lr * 0.2, -0.04), cap=False)
        P.sit_skirt = [lap, drop, band]
        for o in P.sit_skirt:
            o.hide_render = True
    P.blink_seed = random.Random(hash(key) & 0xffff)
    P.blinks = sorted(P.blink_seed.uniform(0, 400) for _ in range(140))
    return P


# ----------------------------------------------------------------- posing
def d(x):
    return math.radians(x)


def rest_pose(P):
    for i, sx in enumerate((1, -1)):
        P.sh[i].rotation_euler = (d(4), d(-sx * 6), 0)
        P.el[i].rotation_euler = (d(-12), 0, 0)
        P.hand[i].rotation_euler = (0, 0, 0)
        P.hip[i].rotation_euler = (0, 0, 0)
        P.knee[i].rotation_euler = (0, 0, 0)
        P.foot[i].rotation_euler = (0, 0, 0)
    P.hips.location.z = P.hipZ
    P.hips.rotation_euler = (0, 0, 0)
    P.chest.rotation_euler = (0, 0, 0)
    P.neck.rotation_euler = (0, 0, 0)
    P.head.rotation_euler = (0, 0, 0)


def face(P, f, mouth=0.0, smile=0.6, blink=None, gaze=(0, 0), brows=0.0, eyes_closed=0.0):
    """mouth 0..1 open, gaze (yaw, pitch) degrees, eyes_closed 0..1 (sleepy)"""
    R = P.R
    m = P.mouth
    m.scale = (R * (0.17 + 0.03 * mouth + 0.03 * smile), R * 0.09, R * (0.01 + 0.13 * mouth))
    m.location.z = -R * (0.43 + 0.06 * mouth)
    P.smile.scale = (1.0 + 0.15 * smile, 1, 1.0 + 0.6 * smile - 0.3)
    P.smile.location.z = -R * 0.02 * (smile - 0.5)
    # blink
    b = 0.0
    if blink is None:
        for t in P.blinks:
            dt = f - t * 30 / 10
            if -2 <= dt <= 3:
                b = max(b, 1 - abs(dt - 0.5) / 2.5)
    else:
        b = blink
    b = max(b, eyes_closed)
    for lid in P.lids:
        lid.rotation_euler.x = d(-32 + 120 * b)
    for g in P.eyes:
        g.rotation_euler = (d(gaze[1]), 0, d(gaze[0]))
    for i, br in enumerate(P.brows):
        br.location.z = R * 0.08 * brows


def look_angles(P, target):
    """yaw, pitch (deg) for P.head to look at world target"""
    hw = P.head.matrix_world.translation
    inv = P.root.matrix_world.to_3x3().inverted()
    v = inv @ (Vector(target) - hw)
    yaw = math.degrees(math.atan2(v.x, -v.y))
    pitch = math.degrees(math.atan2(v.z, math.hypot(v.x, v.y)))
    return yaw, pitch


def walk(P, t, stride=30, arm=25, bob=0.02, speed=1.0, knee=35, run=False):
    """procedural walk cycle; t in seconds"""
    ph = t * speed * 2 * math.pi
    s = math.sin(ph)
    for i, sx in enumerate((1, -1)):
        k = s * sx
        P.hip[i].rotation_euler = (d(stride * k), 0, 0)
        P.knee[i].rotation_euler = (d(knee * max(0, math.sin(ph + (0 if sx > 0 else math.pi) - 0.9))), 0, 0)
        P.foot[i].rotation_euler = (d(8 * k), 0, 0)
        P.sh[i].rotation_euler = (d(-arm * k + (10 if run else 4)), d(-sx * 6), 0)
        P.el[i].rotation_euler = (d(-20 - (50 if run else 10) * (0.5 + 0.5 * -k)), 0, 0)
    P.hips.location.z = P.hipZ + bob * abs(math.cos(ph)) - bob * 0.5
    P.chest.rotation_euler = (d(8 if run else 2), 0, d(4 * s))
    P.hips.rotation_euler = (0, 0, d(-5 * s))


def place(P, loc, yaw_deg):
    P.root.location = loc
    P.root.rotation_euler = (0, 0, math.radians(yaw_deg))


def set_skirt(P, sitting):
    for o in P.stand_skirt:
        o.hide_render = sitting
    for o in P.sit_skirt:
        o.hide_render = not sitting


def sit(P, seat_h, lean=0.0):
    """seated pose; root must be at floor level under the seat. seat_h = seat top above floor"""
    rest_pose(P)
    hh = seat_h + P.lr * 1.15
    P.hips.location.z = hh
    drop = hh - 0.05
    ka = 90 - math.degrees(math.acos(max(-1, min(1, drop / P.l2)))) if drop < P.l2 else 90
    for i, sx in enumerate((1, -1)):
        P.hip[i].rotation_euler = (d(-90), 0, d(sx * -4))
        P.knee[i].rotation_euler = (d(ka), 0, 0)
        P.foot[i].rotation_euler = (d(0), 0, 0)
    P.chest.rotation_euler = (d(lean), 0, 0)
    set_skirt(P, True)


def stand(P):
    rest_pose(P)
    set_skirt(P, False)


def lie(P, loc, yaw):
    """lying on back, head toward local +Y after yaw"""
    rest_pose(P)
    set_skirt(P, False)
    P.root.location = loc
    P.root.rotation_euler = (d(-90), 0, d(yaw))
    for i, sx in enumerate((1, -1)):
        P.sh[i].rotation_euler = (d(0), d(-sx * 4), 0)
        P.el[i].rotation_euler = (d(0), 0, 0)
