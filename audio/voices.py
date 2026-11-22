"""Generate all Malayalam dialogue with Microsoft's neural Malayalam voices (edge-tts, online) and shape each
character with pitch and pace. Each line is spoken in ONE call so the sentence keeps its natural rhythm
(no cutting at punctuation, no inserted silences): that is what makes the conversation flow.

usage: python3 audio/voices.py
writes build/voice/<id>.wav (48 kHz mono), build/voice/meta.json (duration, 30 fps mouth-openness envelope
for lip-sync, and the start time of every word as the voice service reports it, for the subtitle highlight).
mp3s are cached in build/voice/.cache/ (unchanged text/voice/rate/pitch is not fetched again).
"""
import asyncio, hashlib, io, json, os, re, subprocess, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "voice")
CACHE = os.path.join(OUT, ".cache")
FPS = 30
SR = 48000

# voice, pitch, rate: the two Malayalam neural voices (Sobhana, Midhun) cast as five characters
VOICES = {
    "child":    dict(voice="ml-IN-SobhanaNeural", pitch="+30Hz", rate="+4%"),
    "grandma":  dict(voice="ml-IN-SobhanaNeural", pitch="-20Hz", rate="-10%"),
    "grandpa":  dict(voice="ml-IN-MidhunNeural",  pitch="-8Hz",  rate="-10%"),
    "adult":    dict(voice="ml-IN-MidhunNeural",  pitch="+0Hz",  rate="-6%"),
    "narrator": dict(voice="ml-IN-MidhunNeural",  pitch="-20Hz", rate="-8%"),
}


def spoken(text, speaker):
    """what is sent to the voice: in conversation an ellipsis is a breath, not a full stop"""
    if speaker in ("narrator", "adult"):
        return text
    return re.sub(r"\s*\.\.\.\s*", ", ", text).strip(" ,")


async def fetch(text, v, mp3, words_path):
    import edge_tts
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca):                     # behind a TLS-terminating proxy: trust its CA
        import certifi; certifi.where = lambda: ca
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    for attempt in range(3):
        try:
            com = edge_tts.Communicate(text, v["voice"], rate=v["rate"], pitch=v["pitch"], boundary="WordBoundary", proxy=proxy)
            audio, words = bytearray(), []
            async for ch in com.stream():
                if ch["type"] == "audio": audio += ch["data"]
                elif ch["type"] == "WordBoundary": words.append([ch["text"], ch["offset"] / 1e7, ch["duration"] / 1e7])
            if not audio: raise OSError("empty audio")
            open(mp3 + ".part", "wb").write(audio); os.replace(mp3 + ".part", mp3)
            json.dump(words, open(words_path, "w"), ensure_ascii=False)
            return
        except Exception as e:
            if attempt == 2: raise SystemExit(f"voices.py: could not reach Microsoft's speech service: {e}")
            await asyncio.sleep(1.5 * (attempt + 1))


MAX_GAP, KEEP_GAP = 0.35, 0.30


def tighten(y, words):
    """Conversation fluency: the service stops for up to ~1.2 s at '!', '?' and '.'. Any silence inside a line
    longer than MAX_GAP is shortened to KEEP_GAP (20 ms crossfades); word times after each cut move earlier."""
    hop = int(0.01 * SR)
    e = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2)) for i in range(0, len(y) - hop, hop)])
    quiet = e < max(1e-4, 0.03 * np.percentile(e, 95))
    cuts, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            if i > 0 and j < len(quiet) and (j - i) * .01 > MAX_GAP:
                a = i * .01 + KEEP_GAP / 2; b = j * .01 - KEEP_GAP / 2
                cuts.append((a, b))
            i = j
        else:
            i += 1
    f = int(0.02 * SR)
    for a, b in reversed(cuts):
        ia, ib = int(a * SR), int(b * SR)
        x = y[ib:ib + f] * np.linspace(0, 1, f) + y[ia - f:ia] * np.linspace(1, 0, f)
        y = np.concatenate([y[:ia - f], x, y[ib + f:]])
        words = [[w, t - (b - a) - f / SR if t >= b else t, d] for w, t, d in words]
    return y, words


def decode(mp3):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", "-f", "wav", "-"], capture_output=True, check=True)
    y, _ = sf.read(io.BytesIO(r.stdout), dtype="float64")
    return y


def main():
    os.makedirs(CACHE, exist_ok=True)
    story = json.load(open(os.path.join(ROOT, "story.json"), encoding="utf-8"))
    meta = {}
    for ln in story["lines"]:
        v = VOICES[ln["speaker"]]; say = spoken(ln["text"], ln["speaker"])
        key = hashlib.sha1(json.dumps([v, say], ensure_ascii=False).encode()).hexdigest()[:16]
        mp3, wj = os.path.join(CACHE, key + ".mp3"), os.path.join(CACHE, key + ".words.json")
        if not (os.path.exists(mp3) and os.path.exists(wj)):
            asyncio.run(fetch(say, v, mp3, wj))
        y = decode(mp3); words = json.load(open(wj, encoding="utf-8"))
        # trim the service's leading/trailing silence (keep a little air), shift word times to match
        e = np.abs(y) > 0.01 * np.abs(y).max()
        i0 = max(0, int(np.argmax(e)) - int(0.03 * SR)); i1 = min(len(y), len(y) - int(np.argmax(e[::-1])) + int(0.06 * SR))
        y = y[i0:i1]
        words = [[w, t - i0 / SR, d] for w, t, d in words]
        y, words = tighten(y, words)
        i0 = 0
        y = sosfilt(butter(2, 70, "hp", fs=SR, output="sos"), y)
        act = np.abs(y) > 1e-4
        y = y * (0.12 / (np.sqrt(np.mean(y[act] ** 2)) if act.any() else 1))     # same speech RMS for every line
        y = np.clip(y, -0.98, 0.98)
        lead = 0.05
        y = np.concatenate([np.zeros(int(SR * lead)), y, np.zeros(int(SR * 0.1))])
        sf.write(os.path.join(OUT, ln["id"] + ".wav"), y.astype(np.float32), SR)
        wt = [[w, round(max(0.0, t - i0 / SR + lead), 3)] for w, t, d in words]
        hop = SR // FPS
        n = int(np.ceil(len(y) / hop))
        env = np.array([np.sqrt(np.mean(y[k*hop:(k+1)*hop] ** 2)) if len(y[k*hop:(k+1)*hop]) else 0 for k in range(n)])
        env = np.convolve(env, [0.25, 0.5, 0.25], "same")
        env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
        meta[ln["id"]] = dict(speaker=ln["speaker"], text=ln["text"], dur=len(y) / SR, words=wt,
                              env=[round(float(x), 3) for x in env])
        print(ln["id"], round(len(y) / SR, 2), len(wt), "words", flush=True)
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
