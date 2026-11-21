"""Write subtitles_ml-en.srt from the same timeline the page uses (story.js LINES + voice/out/dur.json + fluency cuts/splits)."""
import json, re, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
js = open(os.path.join(HERE, 'story.js'), encoding='utf-8').read()
LINES = [(m[0], float(m[1])) for m in re.findall(r"\{ id: '(\w+)', t: ([\d.]+)", js)]
title0 = float(re.search(r"title0: ([\d.]+)", js).group(1))
CUTS = {'g2': .65}; SPLIT = {'g2': 2.45}
dur = json.load(open(os.path.join(HERE, 'voice/out/dur.json'))); txt = {l['id']: l for l in json.load(open(os.path.join(HERE, 'voice/lines.json'), encoding='utf-8'))}
SUB2 = {'g2': [('ഇപ്പൊ നീ കുടിച്ച ഈ ഇളനീരില്ലേ...', 'This tender coconut you just drank...'), ('അത് എന്റെ അമ്മൂമ്മ നട്ട തെങ്ങിലെയാ.', '...it came from a tree my grandma planted.')]}
cues = []
for i, (id, t) in enumerate(LINES):
    d = dur[id] - CUTS.get(id, 0); end = t + max(1.8, d + .6)
    end = min(end, LINES[i + 1][1] - .12) if i + 1 < len(LINES) else min(end, title0 - .1)
    if id in SPLIT: m = t + SPLIT[id] + .05; cues += [(t, m, *SUB2[id][0]), (m, end, *SUB2[id][1])]
    else: cues.append((t, end, txt[id]['text'], txt[id]['en']))
f = lambda s: f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{int(round(s*1000))%1000:03d}"
with open(os.path.join(HERE, 'subtitles_ml-en.srt'), 'w', encoding='utf-8') as o:
    for k, (a, b, ml, en) in enumerate(cues, 1): o.write(f"{k}\n{f(a)} --> {f(b)}\n{ml}\n{en}\n\n")
print(len(cues), 'cues → subtitles_ml-en.srt')
