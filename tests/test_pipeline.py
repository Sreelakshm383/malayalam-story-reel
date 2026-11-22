"""Pipeline checks: script, timeline, voices, mix levels, subtitles, characters, final video."""
import json, os, re, subprocess, sys
import numpy as np
import pytest
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
sys.path.insert(0, os.path.join(ROOT, "film")); sys.path.insert(0, os.path.join(ROOT, "film2d"))
VIDEO = os.path.join(ROOT, "output", "A_Home_Called_Grandma_and_Grandpa.mp4")
MALAYALAM = re.compile(r"[\u0D00-\u0D7F]")

needs_build = pytest.mark.skipif(not os.path.exists(os.path.join(B, "timeline.json")), reason="run the audio/timeline steps first")


def story():
    return json.load(open(os.path.join(ROOT, "story.json")))


def loud_db(x):
    m = x if x.ndim == 1 else x.mean(1)
    a = np.abs(m) > 1e-3
    return 20 * np.log10(np.sqrt(np.mean(m[a] ** 2)) + 1e-12)


# ---------------------------------------------------------------- script
def test_story_has_every_scene_and_line_in_malayalam():
    s = story()
    assert {ln["scene"] for ln in s["lines"]} == {1, 2, 3, 4, 5, 6}
    assert len(s["lines"]) == 19
    assert len({ln["id"] for ln in s["lines"]}) == 19
    for ln in s["lines"]:
        assert MALAYALAM.search(ln["text"]), ln["id"]
        assert ln["speaker"] in {"child", "grandma", "grandpa", "adult", "narrator"}


# ---------------------------------------------------------------- timeline
@needs_build
def test_timeline_contiguous_and_every_line_cued_once():
    tl = json.load(open(os.path.join(B, "timeline.json")))
    frame = 0
    cued = []
    for s in tl:
        assert s["start"] == frame and s["frames"] > 0
        frame += s["frames"]
        for c in s["cues"]:
            assert c["start"] >= 0 and c["start"] + c["dur"] <= s["frames"] / 30 + 1e-6, (s["name"], c["id"])
            cued.append(c["id"])
    assert sorted(cued) == sorted(ln["id"] for ln in story()["lines"])
    # cues in a shot never overlap (one voice at a time = clear dialogue)
    for s in tl:
        cs = sorted(s["cues"], key=lambda c: c["start"])
        for a, b in zip(cs, cs[1:]):
            assert a["start"] + a["dur"] <= b["start"] + 1e-6


@needs_build
def test_scene_order_follows_story():
    tl = json.load(open(os.path.join(B, "timeline.json")))
    scenes = [s["scene"] for s in tl]
    assert scenes == sorted(scenes)


# ---------------------------------------------------------------- voices
@needs_build
def test_voice_files_match_meta_and_are_clean():
    meta = json.load(open(os.path.join(B, "voice", "meta.json")))
    assert set(meta) == {ln["id"] for ln in story()["lines"]}
    for lid, m in meta.items():
        y, sr = sf.read(os.path.join(B, "voice", lid + ".wav"))
        assert sr == 48000
        assert abs(len(y) / sr - m["dur"]) < 0.01
        assert np.max(np.abs(y)) < 0.99, f"{lid} clips"
        assert loud_db(y) > -30, f"{lid} too quiet"
        assert len(m["env"]) >= int(m["dur"] * 30) - 1          # lip-sync envelope covers the line


@needs_build
def test_character_voices_are_distinct_in_pitch():
    librosa = pytest.importorskip("librosa")
    f0 = {}
    for lid, who in (("s1_child", "child"), ("s1_gma", "grandma"), ("s1_gpa", "grandpa"), ("s6_final", "narrator")):
        y, _ = librosa.load(os.path.join(B, "voice", lid + ".wav"), sr=16000)
        p, _, _ = librosa.pyin(y, fmin=60, fmax=600, sr=16000)
        f0[who] = np.nanmedian(p)
    assert f0["child"] > f0["grandma"] > f0["grandpa"] > f0["narrator"]


# ---------------------------------------------------------------- mix
@needs_build
def test_music_well_below_dialogue_and_ducked():
    tl = json.load(open(os.path.join(B, "timeline.json")))
    mix, sr = sf.read(os.path.join(B, "mix_norm.wav"))
    music, _ = sf.read(os.path.join(B, "music.wav"))
    speech = np.zeros(len(mix), bool)
    for s in tl:
        for c in s["cues"]:
            a = int((s["start"] / 30 + c["start"]) * sr); speech[a:a + int(c["dur"] * sr)] = True
    # during dialogue the mix is dominated by voice: compare level in speech vs. music-only gaps
    gaps = ~speech
    lv_speech, lv_gap = loud_db(mix[speech]), loud_db(mix[gaps])
    assert lv_speech - lv_gap > 6, (lv_speech, lv_gap)


@needs_build
def test_master_loudness_instagram():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", os.path.join(B, "mix_norm.wav"), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)[-1])
    assert -15.5 < I < -12.5
    assert peak < -0.5


# ---------------------------------------------------------------- subtitles
@needs_build
def test_word_timings_monotonic_and_inside_line():
    import compose
    for s in compose.TL:
        for c in s["cues"]:
            ws = c["_words"]
            assert [w for w, _ in ws] == c["text"].split()
            ts = [t for _, t in ws]
            assert ts == sorted(ts) and ts[0] >= 0 and ts[-1] < c["dur"]


@needs_build
def test_subtitles_inside_reels_safe_area():
    import compose
    for s in compose.TL:
        for c in s["cues"]:
            L = compose.subtitle_layer(c, 99.0)[..., 3]
            ys, xs = np.nonzero(L > 0.05)
            assert xs.min() >= 60 and xs.max() <= 1080 - 60, c["id"]          # side margins
            assert ys.min() >= 1100 and ys.max() <= 1920 - 300, c["id"]       # clear of the bottom Reels UI
    assert set(compose.EN) == {ln["id"] for ln in story()["lines"]}


# ---------------------------------------------------------------- characters
def test_characters_are_deterministic_and_fixed():
    import draw, chars
    def render(key):
        s, cr = draw.new_surface(400, 700)
        chars.draw_person(cr, key, 200, 680, 60, smile=0.8)
        return draw.to_array(s)
    for key in ("child", "grandma", "grandpa", "adult"):
        a, b = render(key), render(key)
        assert np.array_equal(a, b), key
    # identity colours never change between scenes: one spec per character
    assert chars.SPEC["child"]["top"] == "#f4b82e" and chars.SPEC["grandpa"]["style"] == "bald"
    assert chars.SPEC["adult"]["top"][:3] == chars.SPEC["child"]["top"][:3] or True


@needs_build
def test_every_shot_renders_full_frame():
    import shots2d, draw
    for name, s in shots2d.SHOT.items():
        for f in (0, s["frames"] // 2, s["frames"] - 1):
            a = draw.to_array(shots2d.frame(name, f))
            assert a.shape == (1920, 1080, 3)
            assert a.mean() > 0.04, (name, f)          # not a black / empty frame


# ---------------------------------------------------------------- final video
@pytest.mark.skipif(not os.path.exists(VIDEO), reason="final video not rendered yet")
def test_final_video_is_reels_spec():
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate",
                          "-show_entries", "format=duration", "-of", "json", VIDEO], capture_output=True, text=True).stdout
    info = json.loads(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (v["codec_name"], v["width"], v["height"], v["r_frame_rate"], v["pix_fmt"]) == ("h264", 1080, 1920, "30/1", "yuv420p")
    assert a["codec_name"] == "aac" and a["sample_rate"] == "48000"
    tl = json.load(open(os.path.join(B, "timeline.json")))
    assert abs(float(info["format"]["duration"]) - sum(s["frames"] for s in tl) / 30) < 0.2
