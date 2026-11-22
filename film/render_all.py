"""Render every shot (on twos at 540x960) with N parallel Blender workers.
usage: python3 film/render_all.py [workers] [shot ...]"""
import json, os, subprocess, sys, threading, queue
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = int(sys.argv[1]) if len(sys.argv) > 1 else 3
only = sys.argv[2:]
tl = json.load(open(os.path.join(ROOT, "build", "timeline.json")))
shots = [s for s in tl if not only or s["name"] in only]
shots.sort(key=lambda s: -s["frames"])
q = queue.Queue()
for s in shots: q.put(s)
def worker(i):
    while True:
        try: s = q.get_nowait()
        except queue.Empty: return
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24", "blender", "-b", "--factory-startup", "-P",
               os.path.join(ROOT, "film", "render.py"), "--", s["name"], "--step", "2", "--scale", "50", "--samples", "8", "--skip"]
        with open(os.path.join(ROOT, "build", f"log_{s['name']}.txt"), "w") as lg:
            r = subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, cwd=ROOT)
        print(f"worker{i} done {s['name']} rc={r.returncode}", flush=True)
ts = [threading.Thread(target=worker, args=(i,)) for i in range(W)]
for t in ts: t.start()
for t in ts: t.join()
print("ALL DONE")
