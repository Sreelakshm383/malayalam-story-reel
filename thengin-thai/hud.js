// The storyteller's placard (subtitles): narrow dark-lacquer board, thin gold line, a small carved seal; Malayalam on top, English under it.
const ML = '600 46px "Noto Serif Malayalam"', EN = '600 38px "Cormorant Garamond"';
function wrap(g, text, font, maxW) {
  g.font = font; const words = text.split(' '), out = []; let cur = '';
  for (const w of words) { const s = cur ? cur + ' ' + w : w; if (g.measureText(s).width > maxW && cur) { out.push(cur); cur = w; } else cur = s; }
  if (cur) out.push(cur); return out;
}
export function placardBox(g, ml, en) {
  const maxW = 860, a = wrap(g, ml, ML, maxW), b = wrap(g, en, EN, maxW);
  g.font = ML; let w = Math.max(...a.map(s => g.measureText(s).width)); g.font = EN; w = Math.max(w, ...b.map(s => g.measureText(s).width));
  const h = 34 + a.length * 64 + b.length * 46, W = Math.min(1040, w + 116);
  return { a, b, w: W, h };
}
export function drawSub(g, ml, en, a = 1, slide = 0, cy = 1560) {
  if (!ml || a <= 0) return null;
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = a;
  const P = placardBox(g, ml, en), x = 540 - P.w / 2, y = cy - P.h / 2 + slide * 18;
  g.shadowColor = 'rgba(0,0,0,.55)'; g.shadowBlur = 18; g.shadowOffsetY = 4;
  const gr = g.createLinearGradient(0, y, 0, y + P.h); gr.addColorStop(0, 'rgba(46,22,14,.93)'); gr.addColorStop(.5, 'rgba(30,14,9,.93)'); gr.addColorStop(1, 'rgba(22,10,7,.93)');
  g.fillStyle = gr; rr(g, x, y, P.w, P.h, 6); g.fill(); g.shadowColor = 'transparent';
  g.strokeStyle = 'rgba(168,129,63,.8)'; g.lineWidth = 1.5; rr(g, x + 6, y + 6, P.w - 12, P.h - 12, 3); g.stroke();
  // carved seal: a small vermilion square with a coconut-palm glyph cut in it
  const sx = x + 18, sy = y + 18, s = 30;
  g.fillStyle = '#b3261b'; rr(g, sx, sy, s, s, 3); g.fill();
  g.strokeStyle = '#f6dcc0'; g.lineWidth = 1.6; g.beginPath(); g.moveTo(sx + 15, sy + 26); g.quadraticCurveTo(sx + 14, sy + 16, sx + 17, sy + 10);
  for (const d of [-1, 1]) { g.moveTo(sx + 17, sy + 10); g.quadraticCurveTo(sx + 17 + d * 7, sy + 4, sx + 17 + d * 11, sy + 11); } g.stroke();
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#f3e2bf';
  let yy = y + 20 + 32;
  g.font = ML; for (const s1 of P.a) { g.fillText(s1, 540 + 14, yy); yy += 64; }
  yy -= 8; g.font = EN; g.fillStyle = '#d9c08f'; for (const s2 of P.b) { g.fillText(s2, 540 + 14, yy); yy += 46; }
  g.restore();
  return P;
}
function rr(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
