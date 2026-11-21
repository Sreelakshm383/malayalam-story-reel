"""Generate all Malayalam dialogue with Meta MMS-TTS (VITS) and shape each
character's voice (pitch / formant / pace) so the five voices are distinct.

usage: python3 audio/voices.py <mms-model-dir>
writes build/voice/<id>.wav (48 kHz mono) and build/voice/meta.json
(duration + 30 fps mouth-openness envelope for lip-sync).
"""
import json, os, re, subprocess, sys, tempfile
import numpy as np, soundfile as sf, torch
from scipy.signal import resample_poly, butter, sosfilt
from transformers import VitsModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "voice")
FPS = 30
SR = 48000

# pitch ratio, formant ratio, speaking rate, noise_scale, extra pause scale
VOICES = {
    "child":    dict(p=2.45, q=1.22, rate=1.00, noise=0.70, pause=0.9),
    "grandma":  dict(p=1.72, q=1.12, rate=0.86, noise=0.60, pause=1.1),
    "grandpa":  dict(p=0.86, q=0.97, rate=0.88, noise=0.60, pause=1.1),
    "adult":    dict(p=1.06, q=1.02, rate=0.86, noise=0.55, pause=1.2),
    "narrator": dict(p=0.84, q=0.94, rate=0.80, noise=0.50, pause=1.5),
}


def chunks(text):
    """split on '...', '!', '?', '.', ',' keeping the pause length after each"""
    parts = re.split(r"(\.\.\.|[!?.,])", text)
    out, cur = [], ""
    for p in parts:
        if p in ("...", "!", "?", ".", ","):
            if cur.strip():
                pause = {"...": 0.55, ",": 0.22}.get(p, 0.35)
                out.append((cur.strip(), pause, p))
            cur = ""
        else:
            cur += p
    if cur.strip():
        out.append((cur.strip(), 0.3, ""))
    return out


def shape(wav, sr, v, tmp):
    """formant shift by resampling, then pitch-correct with rubberband (-F)."""
    q, p = v["q"], v["p"]
    src = os.path.join(tmp, "a.wav"); dst = os.path.join(tmp, "b.wav")
    sf.write(src, wav, sr)
    # playing the 16k audio as if it were sr*q raises pitch+formants by q
    mid = os.path.join(tmp, "m.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af",
                    f"asetrate={int(sr*q)},aresample={SR}", mid], check=True)
    subprocess.run(["rubberband", "-q", "-3", "-F", "-t", f"{q:.5f}", "-f", f"{p/q:.5f}",
                    mid, dst], check=True, capture_output=True)
    y, _ = sf.read(dst)
    return y


def main(model_dir):
    os.makedirs(OUT, exist_ok=True)
    story = json.load(open(os.path.join(ROOT, "story.json")))
    model = VitsModel.from_pretrained(model_dir); tok = AutoTokenizer.from_pretrained(model_dir)
    msr = model.config.sampling_rate
    meta = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, ln in enumerate(story["lines"]):
            v = VOICES[ln["speaker"]]
            model.config.speaking_rate = v["rate"]; model.noise_scale = v["noise"]
            pieces = []
            for j, (txt, pause, punct) in enumerate(chunks(ln["text"])):
                torch.manual_seed(1000 + i * 17 + j)
                x = tok(txt, return_tensors="pt")
                with torch.no_grad():
                    w = model(**x).waveform[0].numpy().astype(np.float64)
                y = shape(w, msr, v, tmp)
                if punct == "?":  # gentle questioning lift on the last 0.35 s
                    pass
                pieces.append(y)
                pieces.append(np.zeros(int(SR * pause * v["pause"])))
            y = np.concatenate(pieces[:-1])
            # light clean-up: high-pass, gentle de-ess shelf, normalise to -16 dBFS-ish RMS
            y = sosfilt(butter(2, 70, "hp", fs=SR, output="sos"), y)
            if ln["speaker"] in ("child", "grandma"):
                y = 0.85 * y + 0.15 * sosfilt(butter(2, 4500, "lp", fs=SR, output="sos"), y) - 0.15 * y * 0
            act = np.abs(y) > 1e-4
            rms = np.sqrt(np.mean(y[act] ** 2)) if act.any() else 1
            y = y * (0.12 / rms)
            y = np.clip(y, -0.98, 0.98)
            y = np.concatenate([np.zeros(int(SR * 0.05)), y, np.zeros(int(SR * 0.1))])
            sf.write(os.path.join(OUT, ln["id"] + ".wav"), y.astype(np.float32), SR)
            # lip-sync envelope: RMS per video frame, smoothed, 0..1
            hop = SR // FPS
            n = int(np.ceil(len(y) / hop))
            env = np.array([np.sqrt(np.mean(y[k*hop:(k+1)*hop] ** 2)) for k in range(n)])
            env = np.convolve(env, [0.25, 0.5, 0.25], "same")
            env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
            meta[ln["id"]] = dict(speaker=ln["speaker"], text=ln["text"], dur=len(y) / SR,
                                  env=[round(float(e), 3) for e in env])
            print(ln["id"], round(len(y) / SR, 2), flush=True)
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
