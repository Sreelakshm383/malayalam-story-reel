import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, render_setup as R, lib
R.reset(); R.setup(res=(1080,1920), scale=50)
R.sky_world(18, 200, 0.7)
R.sun(elev=25, azim=-140, energy=3.5)
g = lib.plane("ground", 20, 20, m=lib.mat("g","#8a6a4a",0.9))
chars = {}
for k, x in (("grandma", -0.55), ("child", 0.05), ("grandpa", 0.6), ("adult", 1.3)):
    P = lib.make_person(k); lib.rest_pose(P); lib.place(P, (x, 0, 0), 0); lib.face(P, 0, smile=0.8); chars[k]=P
cam = R.camera(lens=40, fstop=8)
which = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "all"
if which == "all":
    R.aim(cam, (0.3, -5.2, 1.1), (0.3, 0, 0.85))
else:
    P = chars[which]; h = P.head.matrix_world.translation if False else None
    bpy.context.view_layer.update()
    h = P.head.matrix_world.translation
    R.aim(cam, (h.x+0.15, h.y-1.1, h.z+0.05), h)
t=time.time(); R.render(f"/home/user/malayalam-story-reel/build/test/lineup_{which}.png"); print("T", time.time()-t)
