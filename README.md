# malayalam-story-reel

My Malayalam motivational story video project.

**Film:** *മുത്തശ്ശന്റെയും മുത്തശ്ശിയുടെയും വീട് (A Home Called Grandma & Grandpa)*. It is a 2-minute illustrated short film about a child's summer holidays with his grandparents, made for Instagram Reels and YouTube Shorts.

- Video: 1080 × 1920 (9:16), 30 fps, H.264 + AAC 48 kHz, about 126 s
- Six scenes and 19 Malayalam lines with separate child, grandmother, grandfather, grown-up and narrator voices
- Subtitles highlight the Malayalam word by word, with a smaller English line underneath, kept inside the Reels safe area
- Soft piano and string score kept about 12 dB under the dialogue and ducked during every line
- Quiet background sounds: birds, wind, footsteps, the kitchen fire, crickets, rain and a clock
- Audio is normalised to −14 LUFS for Instagram

## Build

```bash
pip install -r requirements.txt          # plus ffmpeg, rubberband-cli, and Malayalam fonts (Manjari / Noto Sans Malayalam)
./make_film.sh                           # writes output/A_Home_Called_Grandma_and_Grandpa.mp4 and runs the tests
```

The first run downloads the `facebook/mms-tts-mal` voice model from huggingface.co. To use a local copy, set `MMS_MODEL_DIR=/path/to/model`. Set `WORKERS` to the number of CPU cores to use.

## Pipeline

| Step | File | Output |
|---|---|---|
| Script (all Malayalam lines) | `story.json` | |
| Voices: MMS-TTS Malayalam, shaped per character with pitch, formant and pace | `audio/voices.py` | `build/voice/*.wav`, `meta.json` (lip-sync envelopes) |
| Shot list and timing | `film/timeline.py` | `build/timeline.json` |
| Music | `audio/music.py` | `build/music.wav` |
| Background sounds | `audio/ambience.py` | `build/ambience.wav` |
| Mix with music ducked under dialogue | `audio/mix.py` | `build/mix.wav` → `build/mix_norm.wav` |
| Characters (one fixed design each) | `film2d/chars.py` | |
| Backgrounds and props | `film2d/scenes.py` | |
| Shots: acting, lip-sync and camera moves | `film2d/shots2d.py` | |
| Grade, particles, dissolves, titles, subtitles, encode | `film/compose.py` | `output/*.mp4` |
| Tests | `tests/test_pipeline.py` | |

Useful commands:

```bash
python3 film2d/preview2d.py s1_gma s4_story               # contact sheet of shots → build/preview2d/sheet.png
python3 film/compose.py build/frame.png --still 63         # one finished frame at 63 s
python3 -m pytest -q tests                                 # checks (run after the audio steps)
```

The older experimental 3D version (Blender 4.0, EEVEE) is still in `film/lib.py`, `film/sets.py`, `film/shots.py`, `film/render.py` and `film/render_all.py`. It renders very slowly without a GPU, so the 2D illustrated version is the main pipeline.
