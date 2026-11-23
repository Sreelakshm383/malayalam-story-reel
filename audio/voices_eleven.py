"""Generate all Malayalam dialogue with ElevenLabs (eleven_v3 model) instead of the
local MMS model. Same outputs as voices.py: build/<story>/voice/<id>.wav (48 kHz mono)
and meta.json (duration + 30 fps mouth envelope for lip-sync).

usage: REEL_STORY=<story> python3 audio/voices_eleven.py [--only id1,id2] [--force]

The API key is read from ELEVENLABS_API_KEY (in this cloud session the network proxy
adds the real key itself, so any placeholder value works). Responses are cached in
build/<story>/voice/eleven/ so re-runs only pay for changed lines.

Voices: each speaker maps to an ElevenLabs voice id + settings. Defaults below use
ElevenLabs' public premade voices; a story can override them with an "eleven" block:
    "eleven": {"girl": {"voice": "<voice_id>", "pitch": 1.2, "stability": 0.5}}
ElevenLabs has no child voices, so kids use a young female voice raised in pitch
(rubberband, formant-preserving).
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from reel import B, CFG

OUT = os.path.join(B, "voice")
CACHE = os.path.join(OUT, "eleven")
FPS, SR = 30, 48000
MODEL = os.environ.get("ELEVEN_MODEL", "eleven_v3")

# premade voices: Jessica (young F), Matilda (warm older F), Bill (old M), Brian (M),
# Chris (M), George (warm narrator M), Sarah (soft F)
VOICES = {
    "child":      dict(voice="cgSgspJ2msm6clMCkdW9", pitch=1.24, stability=0.5),
    "girl":       dict(voice="cgSgspJ2msm6clMCkdW9", pitch=1.2, stability=0.5),
    "grandma":    dict(voice="XrExE9yKIg1WjnnlVkGX", pitch=1.0, stability=0.6),
    "grandpa":    dict(voice="pqHfZKP75CVOlQylNhV4", pitch=1.0, stability=0.6),
    "adult":      dict(voice="iP95p4xoKVk53GoZ742B", pitch=1.0, stability=0.55),
    "father":     dict(voice="nPczCjzI2devNBz1zQrb", pitch=1.0, stability=0.55),
    "father_old": dict(voice="pqHfZKP75CVOlQylNhV4", pitch=1.0, stability=0.6),
    "woman":      dict(voice="EXAVITQu4vr4xnSDxMaL", pitch=1.0, stability=0.5),
    "narrator":   dict(voice="JBFqnCBsd6RMkjVDRZzb", pitch=1.0, stability=0.6),
    "narrator_f": dict(voice="EXAVITQu4vr4xnSDxMaL", pitch=1.0, stability=0.6),
}
for k, v in CFG.get("eleven", {}).items():
    VOICES[k] = dict(VOICES.get(k, {}), **v)


def tts(text, v):
    body = dict(text=text, model_id=MODEL, language_code="ml",
                voice_settings=dict(stability=v.get("stability", 0.5), similarity_boost=v.get("similarity", 0.75),
                                    style=v.get("style", 0.0), use_speaker_boost=True))
    key = hashlib.sha1(json.dumps([v["voice"], body], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    path = os.path.join(CACHE, key + ".mp3")
    if os.path.exists(path):
        return path
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{v['voice']}?output_format=mp3_44100_128"
    for attempt in range(5):
        req = urllib.request.Request(url, json.dumps(body, ensure_ascii=False).encode(), method="POST", headers={
            "xi-api-key": os.environ.get("ELEVENLABS_API_KEY", "proxy-injected"), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            if e.code == 400 and "language_code" in msg and "language_code" in body:
                body.pop("language_code"); continue          # model auto-detects the language
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(3 * (attempt + 1)); continue
            sys.exit(f"ElevenLabs error {e.code}: {msg}")
    os.makedirs(CACHE, exist_ok=True)
    open(path, "wb").write(data)
    return path


def load(path, v, tmp):
    """mp3 -> 48 kHz mono float, optional formant-preserving pitch shift"""
    wav = os.path.join(tmp, "a.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), wav], check=True)
    if abs(v.get("pitch", 1.0) - 1.0) > 1e-3:
        out = os.path.join(tmp, "b.wav")
        subprocess.run(["rubberband", "-q", "-3", "-F", "-f", f"{v['pitch']:.4f}", wav, out], check=True, capture_output=True)
        wav = out
    y, _ = sf.read(wav)
    return y.astype(np.float64)


def trim(y, thr=0.01):
    a = np.where(np.abs(y) > thr)[0]
    return y[max(0, a[0] - int(0.03 * SR)):a[-1] + int(0.08 * SR)] if len(a) else y


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))
    os.makedirs(OUT, exist_ok=True)
    mp = os.path.join(OUT, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) and not a.force else {}
    with tempfile.TemporaryDirectory() as tmp:
        for ln in CFG["lines"]:
            if only and ln["id"] not in only:
                continue
            v = VOICES[ln["speaker"]]
            y = trim(load(tts(ln.get("tts", ln["text"]), v), v, tmp))
            y = sosfilt(butter(2, 70, "hp", fs=SR, output="sos"), y)
            act = np.abs(y) > 1e-4
            rms = np.sqrt(np.mean(y[act] ** 2)) if act.any() else 1
            y = np.clip(y * (0.12 / rms), -0.98, 0.98)
            y = np.concatenate([np.zeros(int(SR * 0.05)), y, np.zeros(int(SR * 0.1))])
            sf.write(os.path.join(OUT, ln["id"] + ".wav"), y.astype(np.float32), SR)
            hop = SR // FPS
            n = int(np.ceil(len(y) / hop))
            env = np.array([np.sqrt(np.mean(y[k * hop:(k + 1) * hop] ** 2)) for k in range(n)])
            env = np.convolve(env, [0.25, 0.5, 0.25], "same")
            env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
            meta[ln["id"]] = dict(speaker=ln["speaker"], text=ln["text"], dur=len(y) / SR, env=[round(float(e), 3) for e in env])
            print(ln["id"], round(len(y) / SR, 2), flush=True)
    json.dump(meta, open(mp, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
