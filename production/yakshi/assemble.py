"""Cut the 14 Veo/Flow clips to the voice-over timing, lay the ORIGINAL voice-over
under them, burn in Malayalam + English subtitles and the end title.

usage: python3 production/yakshi/assemble.py <voice-over.mp4> <clips_dir> [out.mp4]
clips_dir holds scene01.mp4 ... scene14.mp4 (missing ones become black placeholders).
"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ML = "/usr/share/fonts/opentype/malayalam/Manjari-Bold.otf"
EN = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"

# scene cut points (seconds) on the voice-over master clock
CUTS = [0.00, 3.15, 5.50, 9.30, 13.00, 18.65, 22.80, 24.00, 27.65, 29.85, 32.00, 36.50, 37.90, 42.17, 46.41]

# (start, end, malayalam, english)
SUBS = [
    (0.00, 3.15, "ആരാവണമെന്ന് ചോദിച്ചപ്പോൾ \"യക്ഷി\" എന്നായിരുന്നു ഉത്തരം.", "When asked what she wanted to become, the answer was \"A Yakshi.\""),
    (3.15, 5.50, "അത് കേട്ട് നാലാം ക്ലാസ് മുഴുവൻ ചിരിച്ചപ്പോഴും,", "Even when the whole of Class 4 burst out laughing,"),
    (5.50, 9.30, "ഉത്തരം പറഞ്ഞ ആ ഒമ്പത് വയസ്സുകാരി ചിരിച്ചിരുന്നില്ല.", "the nine-year-old who said it did not laugh."),
    (9.30, 13.00, "ഉറക്കെ പൊട്ടിച്ചിരിക്കും മുഖങ്ങളിലേക്ക് ചൂരൽ പായിച്ചുകൊണ്ട്", "Swinging her cane at the loudly laughing faces,"),
    (13.00, 16.80, "ക്ലാസിനെ നിശ്ശബ്ദമാക്കാൻ ശ്രമിക്കുമ്പോൾ ടീച്ചറുടെ ചുണ്ടിലും കണ്ടു,", "as she tried to silence the class, on the teacher's lips too..."),
    (16.80, 18.65, "അടക്കിപ്പിടിച്ച ഒരു ചിരി.", "...a smile she held back."),
    (18.65, 22.80, "ആ വർഷത്തെ സ്കൂൾ മാഗസിനിൽ ഒരു കവിത വന്നിരുന്നു.", "That year, a poem appeared in the school magazine."),
    (22.80, 24.00, "അതിങ്ങനെയായിരുന്നു:", "It went like this:"),
    (24.00, 25.55, "\"പെണ്ണായ് പിറക്കണം,", "\"Be born a woman,"),
    (25.55, 27.65, "ഇരുട്ടിൽ നടക്കണം,", "walk in the dark,"),
    (27.65, 29.85, "കാമവെറിയന്മാരുടെ നിണം മണക്കണം,", "smell the blood of lustful men,"),
    (29.85, 32.00, "പൊട്ടിച്ചിരിക്കണം,", "laugh out loud,"),
    (32.00, 34.00, "തൊടുമ്പോൾ ഭയക്കണം,", "let them fear to touch,"),
    (34.00, 34.90, "അടുക്കാൻ മടിക്കണം,", "hesitate to come near,"),
    (34.90, 36.50, "ഭയം മറക്കണം,", "forget all fear,"),
    (36.50, 37.90, "യക്ഷിയാവണം.\"", "become a Yakshi.\""),
    (37.90, 42.17, "ആ കവിത വായിച്ചവരാരും പിന്നെ ചിരിച്ചില്ല.", "No one who read that poem ever laughed again."),
]
TITLE_AT = 43.9


def run(cmd):
    subprocess.run(cmd, check=True)


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > maxw and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    return lines + ([cur] if cur else [])


def sub_png(path, ml, en):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    fm = ImageFont.truetype(ML, 54, layout_engine=ImageFont.Layout.RAQM); fe = ImageFont.truetype(EN, 32)
    lm, le = wrap(d, ml, fm, 900), wrap(d, en, fe, 900)
    y = 1440
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dt = ImageDraw.Draw(txt)
    for ln in lm:
        dt.text(((W - dt.textlength(ln, font=fm)) / 2, y), ln, font=fm, fill=(255, 244, 222, 255)); y += 76
    y += 6
    for ln in le:
        dt.text(((W - dt.textlength(ln, font=fe)) / 2, y), ln, font=fe, fill=(235, 225, 210, 235)); y += 46
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(txt.split()[3].filter(ImageFilter.GaussianBlur(7)))
    img.alpha_composite(sh, (0, 3)); img.alpha_composite(sh); img.alpha_composite(txt)
    img.save(path)


def title_png(path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = ImageFont.truetype(ML, 150, layout_engine=ImageFont.Layout.RAQM)
    t = "യക്ഷി"; d = ImageDraw.Draw(img)
    x = (W - d.textlength(t, font=f)) / 2
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).text((x, 820), t, font=f, fill=(255, 150, 40, 255))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18))); img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
    d.text((x, 820), t, font=f, fill=(255, 226, 150, 255))
    img.save(path)


def main():
    vo, clips = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "Yakshi_final.mp4")
    with tempfile.TemporaryDirectory() as tmp:
        segs = []
        for i in range(14):
            need = CUTS[i + 1] - CUTS[i]
            src = os.path.join(clips, f"scene{i + 1:02d}.mp4")
            seg = os.path.join(tmp, f"seg{i:02d}.mp4")
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
            if os.path.exists(src):
                have = dur(src)
                if have < need:   # stretch a short clip in slow motion to fill its slot
                    vf = f"setpts={need / have:.4f}*PTS," + vf
                    start = 0.0
                else:             # use the middle of a long clip
                    start = max(0.0, (have - need) / 2) if have > need + 1.0 else 0.0
                run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", src, "-an", "-vf", vf,
                     "-t", f"{need:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", seg])
                print(f"scene{i + 1:02d}: {have:.2f}s clip -> {need:.2f}s")
            else:
                run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}", "-t", f"{need:.3f}",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", seg])
                print(f"scene{i + 1:02d}: MISSING -> black placeholder {need:.2f}s")
            segs.append(seg)
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
        body = os.path.join(tmp, "body.mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body])
        # overlays: subtitles + title
        inputs, chain, last = ["-i", body, "-i", vo], [], "0:v"
        for k, (a, b, ml, en) in enumerate(SUBS):
            p = os.path.join(tmp, f"sub{k:02d}.png"); sub_png(p, ml, en)
            inputs += ["-loop", "1", "-t", f"{CUTS[-1]:.2f}", "-i", p]
            chain.append(f"[{last}][{k + 2}:v]overlay=0:0:enable='between(t,{a:.2f},{b - 0.04:.2f})'[v{k}]"); last = f"v{k}"
        tp = os.path.join(tmp, "title.png"); title_png(tp)
        ti = len(SUBS) + 2
        inputs += ["-loop", "1", "-t", f"{CUTS[-1]:.2f}", "-i", tp]
        chain.append(f"[{ti}:v]format=rgba,fade=in:st={TITLE_AT}:d=0.8:alpha=1[tt]")
        chain.append(f"[{last}][tt]overlay=0:0:enable='gte(t,{TITLE_AT})',fade=out:st={CUTS[-1] - 0.8:.2f}:d=0.8[vout]")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "1:a",
             "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-t", f"{CUTS[-1]:.2f}", "-movflags", "+faststart", out])
    print("wrote", out)


if __name__ == "__main__":
    main()
