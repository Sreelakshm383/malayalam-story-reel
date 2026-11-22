import math
import bpy
from mathutils import Vector


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup(res=(1080, 1920), scale=100, samples=24, engine='BLENDER_EEVEE'):
    s = bpy.context.scene
    s.render.engine = engine
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = scale
    s.render.fps = 30
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.render.film_transparent = False
    e = s.eevee
    e.taa_render_samples = samples
    e.use_gtao = True; e.gtao_distance = 0.4; e.gtao_factor = 1.2
    e.use_bloom = True; e.bloom_intensity = 0.03; e.bloom_threshold = 1.2; e.bloom_radius = 5.0
    e.use_ssr = True; e.use_ssr_refraction = False
    e.use_soft_shadows = True
    e.shadow_cube_size = '1024'; e.shadow_cascade_size = '2048'
    e.use_shadow_high_bitdepth = True
    e.volumetric_tile_size = '8'; e.volumetric_samples = 48
    e.use_volumetric_shadows = True
    s.view_settings.view_transform = 'Filmic'
    s.view_settings.look = 'Medium High Contrast'
    s.view_settings.exposure = 0.0
    if s.world is None:
        s.world = bpy.data.worlds.new("World")
    return s


def sky_world(sun_elev=12, sun_rot=200, strength=0.6, tint=None, air=1.0, dust=1.5):
    w = bpy.context.scene.world
    w.use_nodes = True
    N = w.node_tree.nodes; L = w.node_tree.links
    N.clear()
    out = N.new("ShaderNodeOutputWorld")
    bg = N.new("ShaderNodeBackground")
    sky = N.new("ShaderNodeTexSky"); sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_rot)
    sky.air_density = air; sky.dust_density = dust; sky.sun_disc = False
    bg.inputs["Strength"].default_value = strength
    if tint:
        mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0; mix.inputs[7].default_value = tint
        L.new(sky.outputs[0], mix.inputs[6]); L.new(mix.outputs[2], bg.inputs[0])
    else:
        L.new(sky.outputs[0], bg.inputs[0])
    L.new(bg.outputs[0], out.inputs[0])
    return sky


def flat_world(color, strength=1.0):
    w = bpy.context.scene.world
    w.use_nodes = True
    N = w.node_tree.nodes; N.clear()
    out = N.new("ShaderNodeOutputWorld"); bg = N.new("ShaderNodeBackground")
    bg.inputs[0].default_value = color; bg.inputs[1].default_value = strength
    w.node_tree.links.new(bg.outputs[0], out.inputs[0])


def sun(name="Sun", elev=12, azim=200, energy=4.0, color=(1.0, 0.72, 0.45), angle=3.0):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy; ld.color = color
    ld.angle = math.radians(angle)
    ld.use_contact_shadow = True
    ob = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(ob)
    # light points along -Z; rotate so it comes from azimuth/elevation
    ob.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim + 180 - 180))
    ob.rotation_euler = (0, math.radians(90 - elev), math.radians(azim))
    return ob


def point(name, loc, energy, color=(1, 0.7, 0.4), radius=0.1, kind='POINT', size=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    ld.shadow_soft_size = radius
    if kind == 'AREA' and size:
        ld.size = size[0]; ld.shape = 'RECTANGLE'; ld.size_y = size[1]
    ld.use_contact_shadow = True
    ob = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def camera(lens=35, fstop=2.8):
    cd = bpy.data.cameras.new("Cam"); cd.lens = lens
    cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24 * 16 / 9 * 0.75
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cd.clip_start = 0.05; cd.clip_end = 400
    ob = bpy.data.objects.new("Cam", cd); bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def aim(cam, loc, target, roll=0.0, focus=None):
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    q = d.to_track_quat('-Z', 'Y')
    cam.rotation_euler = q.to_euler()
    cam.rotation_euler.rotate_axis('Z', math.radians(roll))
    cam.data.dof.focus_distance = (Vector(focus) - Vector(loc)).length if focus is not None else d.length


def volume(size, loc, density=0.02, color=(1, 0.9, 0.8), aniso=0.6):
    import bmesh
    m = bpy.data.materials.new("vol"); m.use_nodes = True
    N = m.node_tree.nodes; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); v = N.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density; v.inputs["Color"].default_value = (*color, 1)
    v.inputs["Anisotropy"].default_value = aniso
    m.node_tree.links.new(v.outputs[0], out.inputs["Volume"])
    me = bpy.data.meshes.new("volbox"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts); bm.to_mesh(me)
    me.materials.append(m)
    ob = bpy.data.objects.new("volbox", me); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
