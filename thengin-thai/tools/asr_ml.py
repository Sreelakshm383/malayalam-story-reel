"""Malayalam speech check: transcribe each voice line with faster-whisper (lang ml) and print character similarity.
usage: python tools/asr_ml.py voice/lines.json voice/out [--model small]   exit 1 if a line is below --threshold"""
import sys, json, re, argparse, difflib, numpy as np, soundfile as sf
ap = argparse.ArgumentParser(); ap.add_argument('lines'); ap.add_argument('dir'); ap.add_argument('--model', default='small'); ap.add_argument('--threshold', type=float, default=0.6)
a = ap.parse_args()
from faster_whisper import WhisperModel
m = WhisperModel(a.model, device='cpu', compute_type='int8')
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.pyenv'))
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate as tr
def latin(s):
    s = tr(s, sanscript.MALAYALAM, sanscript.HK); s = tr(s, sanscript.DEVANAGARI, sanscript.HK)
    return s.lower()
def skel(s):
    # consonant skeleton: fold aspirates, retroflex/dental, voicing and doubling; drop vowels
    s = latin(s); s = re.sub(r'[^a-z]', '', s)
    for x, y in [('zh','l'),('sh','s'),('ch','c'),('th','t'),('dh','t'),('ph','p'),('bh','p'),('kh','k'),('gh','k'),('jh','c'),
                 ('d','t'),('b','p'),('g','k'),('j','c'),('z','l'),('r','l'),('v','w'),('y','')]:
        s = s.replace(x, y)
    s = re.sub(r'[aeiouAEIOURM]', '', s); s = re.sub(r'(.)\1+', r'\1', s); s = s.replace('n','').replace('m','m')
    return s
norm0 = lambda s: re.sub(r'[\s\.,!?…\-“”"\'‍‌]', '', s)
bad = 0
for L in json.load(open(a.lines, encoding='utf-8')):
    x, sr = sf.read(f"{a.dir}/{L['id']}.wav", dtype='float32'); pad = np.zeros(int(0.6 * sr), 'float32')
    segs, _ = m.transcribe(np.concatenate([pad, x, pad]), language='ml', beam_size=5, temperature=0)
    heard = ''.join(s.text for s in segs).strip()
    r = difflib.SequenceMatcher(None, skel(L.get('asr', L['text'])), skel(heard)).ratio()
    ok = r >= a.threshold; bad += not ok
    print(f"{'✓' if ok else '✗'} {L['id']:3} {r:.2f}  want: {L['text']}\n              heard: {heard}")
sys.exit(1 if bad else 0)
