// Carved set pieces: ground strip, coconut palms (five growth stages + the old palm), house, sun/moon, birds, the opening curtain, the title plaque.
// The cloth is 1080 × 1920 (portrait). Ground line at GY.
import { piece, fill, cut, cutLine, cutTaper, ink, within, smooth, poly, lattice, coin, beads, beadLine, meander, cloud, scalesOpen, flameTongue, DYE, canvas, hideTexture } from './carve.js';
import { KD } from './figures.js';
import { mul, T, R, S, set } from './rig.js';
import { drawPiece } from './carve.js';

export const GY = 1330;
export const SAP1 = 560, SAP2 = 330;          // where the two saplings are planted

// ———————————— palm ————————————
function frond(L, seed) {
  return piece([-8, -40, L + 12, L * .42], g => {
    // midrib droops; leaflets on both sides, taper toward the tip; the gaps between leaflets are the carving
    const rib = s => [s * L, -Math.sin(s * Math.PI * .5) * L * .06 + s * s * L * .26];
    const n = Math.round(L / 9);
    g.fillStyle = KD.leaf;
    for (let i = 2; i < n; i++) {
      const s = i / n, [x, y] = rib(s), [x2, y2] = rib(Math.min(1, s + .02)), a = Math.atan2(y2 - y, x2 - x);
      const len = L * .3 * Math.sin(Math.PI * (.12 + s * .85)) * (1 - s * .35);
      for (const side of [-1, 1]) {
        const b = a + side * (1.05 - s * .35) + .25;     // leaflets sweep forward and hang
        const tip = [x + Math.cos(b) * len, y + Math.sin(b) * len + len * .35 * (side > 0 ? 1 : .2)];
        g.beginPath(); g.moveTo(x - Math.cos(a) * 3.2, y - Math.sin(a) * 3.2); g.quadraticCurveTo((x + tip[0]) / 2 + Math.cos(a) * 3, (y + tip[1]) / 2 + Math.sin(a) * 3, tip[0], tip[1]);
        g.quadraticCurveTo((x + tip[0]) / 2 + Math.cos(a) * 8, (y + tip[1]) / 2 + Math.sin(a) * 8, x + Math.cos(a) * 4.4, y + Math.sin(a) * 4.4); g.closePath();
        g.fill(); g.strokeStyle = DYE.ink; g.lineWidth = .8; g.stroke();
      }
    }
    ink(g, 3.2, q => { q.moveTo(0, 0); for (let i = 1; i <= 24; i++) q.lineTo(...rib(i / 24)); }, '#4f3a1a');
  }, { seed });
}
function trunk(h, lean, w0 = 46, w1 = 28, seed = 51) {
  // centre line from (0,0) up to (lean, −h), gently curved
  const C = s => [lean * s * s * .9 + lean * .1 * s + Math.sin(s * 3) * 6, -h * s];
  const minX = Math.min(0, lean) - w0, maxX = Math.max(0, lean) + w0;
  return piece([minX - 10, -h - 10, maxX + 10, 14], g => {
    const L = [], Rr = [], n = 40;
    for (let i = 0; i <= n; i++) { const s = i / n, [x, y] = C(s), w = (w0 + (w1 - w0) * s) / 2 * (i === 0 ? 1.25 : 1); L.push([x - w, y]); Rr.push([x + w, y]); }
    const sh = q => { q.moveTo(...L[0]); for (const p of L) q.lineTo(...p); for (let i = n; i >= 0; i--) q.lineTo(...Rr[i]); q.closePath(); };
    fill(g, '#8a5a30', sh);
    within(g, sh, () => {
      for (let y = 10; y < h - 8; y += 15) {    // the rings of a coconut trunk: tapered slits, alternating
        const s = y / h, [x] = C(s), w = (w0 + (w1 - w0) * s) / 2;
        cutTaper(g, [[x - w * .9, -y + 2], [x - w * .2, -y - 1.5], [x + w * .5, -y], [x + w * .95, -y + 3]], 3.2 - s);
        if ((y / 15 | 0) % 2) coin(g, x + w * .2, -y - 7, 2.6);
      }
    });
    ink(g, 2, sh);
  }, { seed });
}
function nuts(seed) {
  return piece([-46, -12, 46, 52], g => {
    const P = [[-26, 10], [-8, 16], [12, 12], [28, 8], [-16, 32], [4, 34], [22, 28]];
    for (const [x, y] of P) { const s = q => q.ellipse(x, y, 13, 15, 0, 0, 7); fill(g, (x + y) % 3 ? KD.leaf2 : KD.gold, s); cut(g, q => q.arc(x - 3, y - 4, 3, 0, 7)); ink(g, 1.3, s); }
  }, { seed });
}
function sprout(seed) {       // stage 0: a sprouting coconut, half buried, three blades
  return piece([-60, -150, 60, 20], g => {
    const husk = q => q.ellipse(0, -4, 34, 22, -.15, 0, 7); fill(g, KD.husk, husk);
    within(g, husk, () => { for (let k = -3; k <= 3; k++) cutLine(g, 1.2, q => { q.moveTo(-30, k * 6); q.quadraticCurveTo(0, k * 7 - 6, 30, k * 5); }); });
    ink(g, 1.6, husk);
    for (const [a, l] of [[-.32, 120], [.05, 140], [.38, 108]]) {
      const bl = q => { q.save(); q.translate(4, -18); q.rotate(a); smooth(q, [[-3, 0], [-11, -l * .4], [-5, -l * .8], [0, -l], [5, -l * .8], [11, -l * .4], [3, 0]]); q.restore(); };
      fill(g, KD.leaf2, bl);
      cutLine(g, 1.4, q => { q.save(); q.translate(4, -18); q.rotate(a); q.moveTo(0, -8); q.lineTo(0, -l * .85); q.restore(); });
      ink(g, 1.3, bl);
    }
  }, { seed });
}
// Palm spec per stage: trunk height, lean, frond count/length, nuts. Stage 0 = sprout.
export const STAGES = [null, { h: 0, lean: 0, n: 5, L: 120, spread: 2.3 }, { h: 110, lean: 10, n: 7, L: 180, spread: 2.7 }, { h: 420, lean: 50, n: 9, L: 240, spread: 3.0 },
  { h: 760, lean: 110, n: 11, L: 280, spread: 3.3 }, { h: 820, lean: 120, n: 12, L: 300, spread: 3.4, nuts: true }];
const PALMS = {};
export function buildPalm(key, spec, seed) {
  if (PALMS[key]) return PALMS[key];
  const o = { spec, fronds: [], seed };
  if (spec === 'sprout') o.sprout = sprout(seed);
  else {
    if (spec.h > 0) o.trunk = trunk(spec.h, spec.lean, spec.h > 300 ? 50 : 36, spec.h > 300 ? 30 : 26, seed);
    for (let i = 0; i < spec.n; i++) o.fronds.push(frond(spec.L * (.82 + .3 * ((i * 37 % 10) / 10)), seed + i));
    if (spec.nuts) o.nuts = nuts(seed + 50);
  }
  PALMS[key] = o; return o;
}
// draw a palm with its base at (x, GY); sway = small wind angle; Cam = camera matrix
export function drawPalm(g, Cam, P, x, t, opt = {}) {
  const sc = opt.sc || 1, al = opt.alpha ?? 1, flip = opt.flip || 1;
  g.save(); g.globalCompositeOperation = 'multiply'; g.globalAlpha = al; if (opt.blur > .3) g.filter = `blur(${opt.blur.toFixed(1)}px)`;
  const B = mul(Cam, mul(T(x, (opt.y ?? GY) + 4), S(sc * flip, sc)));
  if (P.sprout) { set(g, B); drawPiece(g, P.sprout); g.restore(); return; }
  const sp = P.spec, top = [sp.lean + Math.sin(3) * 6, -sp.h];
  // fronds fan from the crown; the outer ones droop. Each sways on its own (hand-held / wind)
  const n = sp.n;
  for (let i = 0; i < n; i++) {
    const u = n === 1 ? .5 : i / (n - 1), side = u < .5 ? -1 : 1;
    let a = -Math.PI / 2 + (u - .5) * sp.spread + Math.sin(t * 1.3 + i * 1.7) * .035 + (opt.wind || 0) * .06 * Math.sin(t * 2.1 + i);
    const M = mul(B, mul(T(top[0], top[1] + (sp.h ? 6 : -4)), mul(R(a), S(1, side < 0 ? -1 : 1))));
    // a frond is drawn along +x; flip it for the left half so its leaflets hang down on both sides
    set(g, M); drawPiece(g, P.fronds[i]);
  }
  if (P.trunk) { set(g, B); drawPiece(g, P.trunk); }
  if (P.nuts) { set(g, mul(B, T(top[0], top[1] + 14))); drawPiece(g, P.nuts); }
  g.restore();
}

// ———————————— ground strip, soil, house, sky pieces ————————————
let SC = null;
export function buildScenery() {
  if (SC) return SC;
  const ground = piece([-20, -30, 1100, 90], g => {
    const s = q => smooth(q, [[-20, 0], [200, -6], [420, 2], [640, -4], [860, 3], [1100, -2], [1100, 90], [-20, 90]].concat([]), true);
    fill(g, KD.earth, q => poly(q, [[-20, 0], [140, -5], [300, 1], [470, -4], [640, 0], [820, -6], [960, 1], [1100, -3], [1100, 90], [-20, 90]]));
    within(g, q => poly(q, [[-20, 0], [140, -5], [300, 1], [470, -4], [640, 0], [820, -6], [960, 1], [1100, -3], [1100, 90], [-20, 90]]), () => {
      meander(g, -10, 34, 1100, 9, 2.4);
      for (let x = 10; x < 1090; x += 44) coin(g, x, 66, 8);
      for (let x = 30; x < 1090; x += 88) cutTaper(g, [[x, 10], [x + 14, 14], [x + 30, 12]], 3);
    });
    ink(g, 2.2, q => { q.moveTo(-20, 0); for (const p of [[140, -5], [300, 1], [470, -4], [640, 0], [820, -6], [960, 1], [1100, -3]]) q.lineTo(...p); });
    ink(g, 2.2, q => { q.moveTo(-20, 88); q.lineTo(1100, 88); });
  }, { seed: 61, ss: 2 });
  const mound = piece([-70, -30, 70, 6], g => { const s = q => smooth(q, [[-66, 4], [-40, -14], [-10, -24], [24, -20], [52, -10], [66, 4]]); fill(g, '#8a5a30', s); within(g, s, () => beads(g, [[-30, -6], [-8, -12], [14, -8], [36, -2], [-46, 0]], 3.2)); ink(g, 1.6, s); }, { seed: 62 });
  const house = piece([-180, -330, 200, 6], g => {
    const wall = q => poly(q, [[-130, 0], [-130, -150], [150, -150], [150, 0]]);
    fill(g, KD.hide2, wall);
    within(g, wall, () => { lattice(g, 50, -120, 120, -40, 12, 2.6); g.fillStyle = DYE.ink; g.fillRect(-80, -120, 70, 120); });
    cut(g, q => { q.rect(-74, -114, 26, 52); q.rect(-42, -114, 26, 52); });
    ink(g, 2, wall); ink(g, 2, q => q.rect(50, -120, 70, 80));
    const roof = q => poly(q, [[-178, -140], [-60, -300], [80, -300], [198, -140]]);
    fill(g, KD.red, roof); within(g, roof, () => scalesOpen(g, -180, -296, 200, -146, 10)); ink(g, 2.2, roof);
    fill(g, DYE.ink, q => poly(q, [[-60, -300], [-70, -326], [-50, -312], [70, -312], [90, -326], [80, -300]]));   // the ridge with curled ends
    for (const x of [-120, 140]) { fill(g, DYE.ink, q => q.rect(x - 5, -150, 10, 150)); }
  }, { seed: 63 });
  const sun = piece([-110, -110, 110, 110], g => {
    const tongues = q => { for (let k = 0; k < 14; k++) { q.save(); q.rotate(k * Math.PI * 2 / 14); q.translate(0, -62); flameTongue(q, 38, 22, k % 2 ? 1 : -1); q.restore(); } };
    fill(g, KD.orange, tongues, 'nonzero'); ink(g, 1.2, tongues);
    const d = q => q.arc(0, 0, 66, 0, 7); fill(g, KD.yellow, d);
    within(g, d, () => { for (let r = 14; r < 64; r += 13) beads(g, Array.from({ length: Math.round(r / 3.4) }, (_, i) => { const a = i / Math.round(r / 3.4) * Math.PI * 2; return [Math.cos(a) * r, Math.sin(a) * r]; }), 2.6); });
    ink(g, 2, d);
  }, { seed: 64 });
  const moon = piece([-80, -80, 80, 80], g => {
    const m = q => { q.arc(0, 0, 62, 0, 7); q.arc(24, -12, 54, 0, 7, true); };
    fill(g, KD.hide2, m, 'evenodd'); within(g, m, () => { cloud(g, -30, 10, 12, 0, 1.3); cloud(g, -14, 38, 9, 2, 1.2, -1); }); ink(g, 1.8, q => { q.arc(0, 0, 62, 0, 7); }); ink(g, 1.6, q => q.arc(24, -12, 54, 2.1, 4.8));
  }, { seed: 65 });
  const bird = [0, 1].map(w => piece([-40, -30, 40, 20], g => {
    const b = q => { q.moveTo(-26, 0); q.quadraticCurveTo(-12, w ? -22 : 8, 0, 0); q.quadraticCurveTo(12, w ? -22 : 8, 26, 0); q.quadraticCurveTo(12, w ? -14 : 14, 0, 6); q.quadraticCurveTo(-12, w ? -14 : 14, -26, 0); };
    fill(g, DYE.ink, b);
  }, { seed: 66 + w }));
  // opening curtain: the cloth all dark hide; one carved hole shaped like a coconut sapling
  const curtain = piece([0, 0, 1080, 1920], g => {
    g.fillStyle = '#3a1c0c'; g.fillRect(0, 0, 1080, 1920);
    const cx = 540, cy = 1060;
    cut(g, q => { q.ellipse(cx, cy + 40, 52, 32, -.12, 0, 7); });
    for (const [a, l] of [[-.36, 240], [.04, 290], [.4, 220]]) cut(g, q => { q.save(); q.translate(cx + 6, cy + 10); q.rotate(a); smooth(q, [[-4, 0], [-22, -l * .4], [-10, -l * .8], [0, -l], [10, -l * .8], [22, -l * .4], [4, 0]]); q.restore(); }, 'nonzero');
    cutLine(g, 2, q => { q.moveTo(40, 1700); q.lineTo(1040, 1700); });
    for (let x = 80; x < 1040; x += 80) coin(g, x, 1760, 14);
    for (let x = 80; x < 1040; x += 80) coin(g, x, 160, 14);
    meander(g, 60, 230, 1020, 12, 3);
  }, { seed: 67, ss: 1 });
  SC = { ground, mound, house, sun, moon, bird, curtain };
  return SC;
}

// Title plaque: dark hide, the words cut through so they glow with the lamp
let PLQ = null;
export function titlePlaque() {
  if (PLQ) return PLQ;
  PLQ = piece([-430, -200, 430, 200], g => {
    const b = q => smooth(q, [[-410, -150], [-300, -186], [0, -176], [300, -186], [410, -150], [420, 0], [410, 150], [300, 184], [0, 176], [-300, 184], [-410, 150], [-420, 0]]);
    fill(g, '#3b1d0d', b);
    within(g, b, () => {
      meander(g, -380, -136, 380, 9, 2.6); meander(g, -380, 150, 380, 9, 2.6);
      for (const x of [-372, 372]) for (const y of [-110, 110]) coin(g, x, y, 15);
      cloud(g, -372, 0, 24, 0, 3); cloud(g, 372, 0, 24, Math.PI, 3, -1);
      g.save(); g.globalCompositeOperation = 'destination-out'; g.fillStyle = '#000'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.font = '700 98px "Noto Serif Malayalam"'; g.fillText('തെങ്ങിൻതൈ', 0, -28);
      g.font = '600 50px "Cormorant Garamond"'; g.letterSpacing = '5px'; g.fillText('THE COCONUT SAPLING', 0, 90);
      g.restore();
    });
    ink(g, 3, b);
  }, { seed: 71, ss: 2 });
  return PLQ;
}
