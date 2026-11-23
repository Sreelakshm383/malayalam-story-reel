"""Subtitles of the source clip, re-typeset cleanly after painting.

Each entry: (start, end, text, align, x, cy, width, colour)
  x/cy/width are in SOURCE pixels (760x576): x is the left edge, centre or right edge
  depending on align ('l', 'c', 'r'); cy is the vertical centre; width is the
  original text width (used to size the font and to erase the old text).
"""
WHITE = (250, 246, 238)
GOLD = (236, 200, 120)
RED = (244, 78, 88)

SUBS = [
    (0.30, 2.37, "I want to see her face", "c", 381, 508, 298, WHITE),
    (3.00, 5.27, "How could you do this?", "c", 383, 508, 334, WHITE),
    (6.50, 9.57, "I want to see her face", "c", 381, 508, 298, WHITE),
    (11.50, 12.77, "Why did you call me pushpa?", "r", 727, 171, 424, WHITE),
    (13.60, 15.17, "You both have the same face", "r", 746, 202, 377, WHITE),
    (15.40, 16.47, "Same eyes", "l", 119, 313, 152, WHITE),
    (17.45, 18.17, "Same nose", "l", 118, 230, 161, WHITE),
    (18.20, 19.27, "Same mouth", "l", 47, 503, 187, WHITE),
    (20.35, 22.27, "An unbelievable resemblance", "r", 737, 107, 426, WHITE),
    (25.20, 26.37, "You were mesmerised by me", "r", 743, 90, 405, WHITE),
    (30.90, 31.67, "You should be a good man", "c", 381, 528, 377, WHITE),
    (32.40, 33.37, "Am I not a good man?", "l", 31, 531, 318, GOLD),
    (34.30, 35.37, "However rich and famous you become...", "c", 380, 509, 570, WHITE),
    (35.80, 37.07, "You must not change", "c", 381, 509, 301, WHITE),
    (37.45, 37.97, "And if I do?", "l", 48, 511, 163, GOLD),
    (38.95, 39.77, "I will push you", "l", 280, 290, 205, RED),
]

def active(t):
    return [s for s in SUBS if s[0] <= t < s[1]]

def src_box(s, pad=10, half_h=17):
    _, _, _, align, x, cy, w, _ = s
    x0 = {"l": x, "c": x - w / 2, "r": x - w}[align]
    return int(x0 - pad), int(cy - half_h), int(x0 + w + pad), int(cy + half_h)
