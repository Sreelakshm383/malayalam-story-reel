import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shots2d
from PIL import Image
import numpy as np, draw
out = os.path.join(shots2d.B, "preview2d"); os.makedirs(out, exist_ok=True)
names = sys.argv[1:] or list(shots2d.FUNCS)
ims = []
for n in names:
    f = int(shots2d.SHOT[n]["frames"] * 0.6)
    s = shots2d.frame(n, f)
    a = (draw.to_array(s) * 255).astype(np.uint8)
    ims.append(Image.fromarray(a).resize((270, 480)))
cols = 6
sheet = Image.new("RGB", (270 * cols, 480 * ((len(ims) + cols - 1) // cols)))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 270, (i // cols) * 480))
sheet.save(os.path.join(out, "sheet.png")); print("ok", len(ims))
