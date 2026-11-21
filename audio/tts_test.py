import sys, torch, soundfile as sf
from transformers import VitsModel, AutoTokenizer
m = VitsModel.from_pretrained(sys.argv[1]); t = AutoTokenizer.from_pretrained(sys.argv[1])
x = t("എന്റെ കുട്ടി വന്നോ! വാ മുത്തേ...", return_tensors="pt")
print(t.convert_ids_to_tokens(x.input_ids[0])[:40])
torch.manual_seed(0)
with torch.no_grad(): w = m(**x).waveform[0].numpy()
sf.write(sys.argv[2], w, m.config.sampling_rate); print(len(w)/m.config.sampling_rate)
