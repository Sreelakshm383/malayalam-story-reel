"""Generic final cut: Veo/Flow clips + finished soundtrack + subtitles + title cards.

usage: python3 production/assemble_episode.py <spec.json> <clips_dir> [out.mp4]
spec.json (written by an episode's build_audio.py) holds:
  audio  soundtrack path (relative to the repo root)
  shots  [{name, start, end}]  clip file = <clips_dir>/<name>.mp4 (a missing clip becomes a black placeholder)
  subs   [{start, end, ml, en}]
  cards  [{text, sub, start, end}]  big gold title cards (episode title, "to be continued")
"""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ML = "/usr/share/fonts/opentype/malayalam/Manjari-Bold.otf"
EN = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
ENB = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd):
    subprocess.run(cmd, check=True)


def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                                capture_output=True, text=True, check=True).stdout.strip())


def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > maxw and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    return lines + ([cur] if cur else [])


def shadowed(img, txt, blur=7):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sh.putalpha(txt.split()[3].filter(ImageFilter.GaussianBlur(blur)))
    img.alpha_composite(sh, (0, 3)); img.alpha_composite(sh); img.alpha_composite(txt)


def sub_png(path, ml, en):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    fm = ImageFont.truetype(ML, 52, layout_engine=ImageFont.Layout.RAQM); fe = ImageFont.truetype(EN, 31)
    y = 1430
    for ln in wrap(d, ml, fm, 920):
        d.text(((W - d.textlength(ln, font=fm)) / 2, y), ln, font=fm, fill=(255, 246, 228, 255)); y += 74
    y += 6
    for ln in wrap(d, en, fe, 920):
        d.text(((W - d.textlength(ln, font=fe)) / 2, y), ln, font=fe, fill=(236, 228, 214, 235)); y += 44
    shadowed(img, txt); img.save(path)


def card_png(path, text, sub):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = ImageFont.truetype(ML, 120, layout_engine=ImageFont.Layout.RAQM); fs = ImageFont.truetype(ENB, 30)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    x = (W - d.textlength(text, font=f)) / 2
    d.text((x, 800), text, font=f, fill=(255, 170, 60, 255))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(16)))
    t = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dt = ImageDraw.Draw(t)
    dt.text((x, 800), text, font=f, fill=(255, 230, 170, 255))
    if sub:
        s2 = "   ".join(sub.split(" "))
        dt.text(((W - dt.textlength(s2, font=fs)) / 2, 980), s2, font=fs, fill=(255, 240, 220, 230))
    shadowed(img, t, 9); img.save(path)


def main():
    spec = json.load(open(sys.argv[1])); clips = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "episode_final.mp4")
    audio = os.path.join(ROOT, spec["audio"]); total = spec["total"]
    with tempfile.TemporaryDirectory() as tmp:
        segs = []
        for sh in spec["shots"]:
            need = sh["end"] - sh["start"]
            src = os.path.join(clips, sh["name"] + ".mp4"); seg = os.path.join(tmp, sh["name"] + ".mp4")
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
            if os.path.exists(src):
                have = dur(src); start = 0.0
                if have < need:
                    vf = f"setpts={need / have:.4f}*PTS," + vf
                elif have > need + 1.0:
                    start = (have - need) / 2
                run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", src, "-an", "-vf", vf, "-t", f"{need:.3f}",
                     "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", seg])
                print(f"{sh['name']}: {have:.2f}s clip -> {need:.2f}s")
            else:
                label = sh.get("label", sh["name"]).replace(":", "\\:").replace("'", "")
                run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x101014:s={W}x{H}:r={FPS}", "-t", f"{need:.3f}",
                     "-vf", f"drawtext=fontfile={ENB}:text='{label}':fontcolor=0x8a8070:fontsize=40:x=(w-tw)/2:y=600",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", seg])
                print(f"{sh['name']}: MISSING -> placeholder {need:.2f}s")
            segs.append(seg)
        lst = os.path.join(tmp, "list.txt"); open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
        body = os.path.join(tmp, "body.mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body])
        inputs, chain, last, n = ["-i", body, "-i", audio], [], "0:v", 2
        for k, s in enumerate(spec["subs"]):
            p = os.path.join(tmp, f"sub{k:02d}.png"); sub_png(p, s["ml"], s["en"])
            inputs += ["-loop", "1", "-t", f"{total:.2f}", "-i", p]
            chain.append(f"[{last}][{n}:v]overlay=0:0:enable='between(t,{s['start'] - 0.05:.2f},{s['end'] + 0.25:.2f})'[s{k}]")
            last = f"s{k}"; n += 1
        for k, c in enumerate(spec.get("cards", [])):
            p = os.path.join(tmp, f"card{k}.png"); card_png(p, c["text"], c.get("sub"))
            inputs += ["-loop", "1", "-t", f"{total:.2f}", "-i", p]
            fo = min(c["end"], total) - 0.7
            chain.append(f"[{n}:v]format=rgba,fade=in:st={c['start']:.2f}:d=0.7:alpha=1,fade=out:st={fo:.2f}:d=0.7:alpha=1[c{k}]")
            chain.append(f"[{last}][c{k}]overlay=0:0:enable='between(t,{c['start']:.2f},{c['end']:.2f})'[k{k}]")
            last = f"k{k}"; n += 1
        chain.append(f"[{last}]fade=in:st=0:d=0.6,fade=out:st={total - 0.8:.2f}:d=0.8[vout]")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "1:a",
             "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", "-movflags", "+faststart", out])
    print("wrote", out)


if __name__ == "__main__":
    main()
