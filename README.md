# malayalam-story-reel

My Malayalam motivational story video project.

**Film:** *മുത്തശ്ശന്റെയും മുത്തശ്ശിയുടെയും വീട് (A Home Called Grandma & Grandpa)*. It is a 2-minute illustrated short film about a child's summer holidays with his grandparents, made for Instagram Reels and YouTube Shorts.

- Video: 1080 × 1920 (9:16), 30 fps, H.264 + AAC 48 kHz, about 106 s
- Six scenes and 19 Malayalam lines with separate child, grandmother, grandfather, grown-up and narrator voices
- Subtitles highlight the Malayalam word by word, with a smaller English line underneath, kept inside the Reels safe area
- Natural, flowing conversation: Microsoft's neural Malayalam voices (Sobhana, Midhun), each line spoken in one go, long pauses inside a line shortened to 0.3 s, replies following each other with about 0.2–0.45 s between speakers
- Levels: dialogue 100 %, background sound (music + ambience) 75 %
- Soft piano and string score kept well under the dialogue and ducked during every line
- Quiet background sounds: birds, wind, footsteps, the kitchen fire, crickets, rain and a clock
- Audio is normalised to −14 LUFS for Instagram

## Build

```bash
pip install -r requirements.txt          # plus ffmpeg and fonts: Manjari (fonts-smc-manjari) and Noto Sans (fonts-noto-core)
./make_film.sh                           # writes output/A_Home_Called_Grandma_and_Grandpa.mp4 and runs the tests
```

The voices come from Microsoft's online speech service through edge-tts, so the first run needs a connection to speech.platform.bing.com; the audio is cached in `build/voice/.cache/`. Check Microsoft's terms before using the voices commercially. Set `WORKERS` to the number of CPU cores to use.

## Pipeline

| Step | File | Output |
|---|---|---|
| Script (all Malayalam lines) | `story.json` | |
| Voices: Microsoft neural Malayalam (edge-tts), cast per character with pitch and pace; pauses tightened for flowing conversation | `audio/voices.py` | `build/voice/*.wav`, `meta.json` (lip-sync envelopes, word timings) |
| Shot list and timing | `film/timeline.py` | `build/timeline.json` |
| Music | `audio/music.py` | `build/music.wav` |
| Background sounds | `audio/ambience.py` | `build/ambience.wav` |
| Mix: dialogue 100 %, background 75 %, music ducked under dialogue | `audio/mix.py` | `build/mix.wav` → `build/mix_norm.wav` |
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
