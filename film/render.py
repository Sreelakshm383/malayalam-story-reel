"""blender -b -P film/render.py -- <shot> [--start N] [--end N] [--step K] [--scale P] [--samples S] [--out DIR]"""
import sys, os, time, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import render_setup as R, shots, lib

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("shot"); ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=-1)
ap.add_argument("--step", type=int, default=1); ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--samples", type=int, default=24); ap.add_argument("--out", default=None)
ap.add_argument("--res", default="1080x1920"); ap.add_argument("--skip", action="store_true")
a = ap.parse_args(argv)

tl, meta = shots.timeline()
os.makedirs(os.path.join(shots.ROOT, "build"), exist_ok=True)
json.dump(tl, open(os.path.join(shots.ROOT, "build", "timeline.json"), "w"), ensure_ascii=False, indent=1)
if a.shot == "timeline":
    print("TOTAL", sum(s["frames"] for s in tl) / 30); sys.exit(0)

shot = next((s for s in tl if s["name"] == a.shot), dict(name=a.shot, start=0, frames=1, scene=0, cues=[]))
R.reset()
res = tuple(int(x) for x in a.res.split("x"))
R.setup(res=res, scale=a.scale, samples=a.samples)
ctx = shots.Ctx(shot, meta)
anim = shots.SHOT_FUNCS[a.shot](ctx)
out = a.out or os.path.join(shots.ROOT, "build", "frames", a.shot)
os.makedirs(out, exist_ok=True)
end = shot["frames"] if a.end < 0 else min(a.end, shot["frames"])
for f in range(a.start, end, a.step):
    if a.skip and os.path.exists(os.path.join(out, f"{f:04d}.png")):
        continue
    t0 = time.time()
    anim(f, f / 30.0)
    bpy.context.view_layer.update()
    R.render(os.path.join(out, f"{f:04d}.png"))
    print(f"FRAME {a.shot} {f} {time.time() - t0:.2f}s", flush=True)
