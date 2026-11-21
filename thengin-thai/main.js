// Thengin Thai (The Coconut Sapling) — shadow puppetry, vertical 1080×1920
import { makeGL } from './gl.js';
import { canvas, drawPiece } from './carve.js';
import { clamp, lerp, seg, ss, eio, eo, ei, back, vnoise, hash, track } from '/core/lib.js';
import { mul, T as Tm, R as Rm, S as Sm, ap, set, drawFigure, drawRods } from './rig.js';
import { buildCast, KD } from './figures.js';
import { buildScenery, buildPalm, drawPalm, STAGES, GY, SAP1, SAP2, titlePlaque } from './scenery.js';
import { drawFrame } from './stage.js';
import { drawSub, placardBox } from './hud.js';
import { T, DUR, LINES, SHOTS, shotAt, SPLIT, editedDur } from './story.js';

const qs = new URLSearchParams(location.search);
const W = 1080, H = 1920;
const [trc, tr] = canvas(W, H), [frc, fr] = canvas(W, H);
const GL = makeGL(document.getElementById('gl'));
for (const f of ['600', '700']) await document.fonts.load(`${f} 46px "Noto Serif Malayalam"`, 'തെങ്ങിൻതൈ');
for (const f of ['600', '700']) await document.fonts.load(`${f} 40px "Cormorant Garamond"`);
const CAST = buildCast(), SC = buildScenery(), PLQ = titlePlaque();
const OLDPALM = buildPalm('old', { h: 860, lean: -120, n: 12, L: 290, spread: 3.4, nuts: true }, 300);
const SPROUT = buildPalm('sprout', 'sprout', 200);
const GROW = STAGES.map((s, i) => i ? buildPalm('st' + i, s, 210 + i * 20) : SPROUT);
let DURS = {}, TEXT = [];
try { DURS = await (await fetch('voice/out/dur.json')).json(); TEXT = await (await fetch('voice/lines.json')).json(); } catch (e) { }
const E = (t, a, b) => ss(seg(t, a, b));
const tremor = (t, s, a = 1) => [(vnoise(t * 2.1 + s) - .5) * 3 * a, (vnoise(t * 2.7 + s + 9) - .5) * 2.4 * a, (vnoise(t * 1.7 + s + 4) - .5) * .018 * a];
const dur = id => editedDur(id, DURS[id] || 2);
const lineAt = (id) => LINES.find(l => l.id === id);
const speaking = (id, t) => { const l = lineAt(id); return l && t >= l.t && t < l.t + dur(id); };
const talk = (id, t, s) => speaking(id, t) ? Math.sin((t - lineAt(id).t) * 9 + s) * .03 + Math.sin((t - lineAt(id).t) * 3.1) * .025 : 0;

// ================= Lamps (the light is the world) =================
const LP = [[540, 820], [200, 1160], [880, 1160]];
const flick = (t, k) => 1 + .06 * (vnoise(t * 7 + k * 13) - .5) * 2 + .03 * Math.sin(t * 23 + k);
const flare = (t, t0, d = .4) => t < t0 ? 0 : (t - t0 < d ? lerp(0, 1, eo((t - t0) / d)) + .45 * Math.sin((t - t0) / d * Math.PI) : 1);
function lamps(t) {
  let I = [flare(t, T.lamp0, .5), flare(t, T.lamp1), flare(t, T.lamp2)];
  // the years: each year dims to night (one low lamp) and relights at the swap beat
  for (const s of T.swaps) {
    if (t > s - .8 && t < s + .5) {
      const dn = E(t, s - .8, s - .45), up = flare(t, s, .32);
      I = I.map((v, k) => k === 0 ? lerp(1, .42, dn) * (t >= s ? 1 : 1) : (t < s ? v * (1 - dn) : up));
      if (t >= s) I[0] = lerp(.42, 1, eo(seg(t, s, s + .32))) + .3 * Math.sin(seg(t, s, s + .32) * Math.PI);
    }
  }
  let dx = 0;
  if (t > T.carry0) { const u = eio(seg(t, T.carry0, T.carry1)); dx = -820 * u; I = I.map((v, k) => v * (1 - u * (k === 2 ? 1.3 : k === 0 ? .9 : .75))); }
  if (t > T.carry1) I = I.map(() => 0);
  return LP.map(([x, y], k) => [x + dx * (k === 2 ? 1.25 : 1), y, Math.max(0, I[k] * flick(t, k)), .95]);
}
const night = t => { for (const s of T.swaps) if (t > s - .5 && t < s) return true; return false; };

// ================= Performers =================
const GM = { x: 720, sc: 1.25, dir: -1 }; GM.y = GY - 74 * GM.sc;
const W2 = (P, lx, ly) => [P.x + P.dir * lx * P.sc, P.y + ly * P.sc];          // figure-local → world (ignoring lean)
// Appu's track (boy): position over time
const APPUX = track([[T.run0, [-80]], [T.run1, [380]], [T.freeze, [400]], [T.walk0, [400]], [T.walk1, [525]], [30, [525]]]);
function appuBoyX(t) { return APPUX(t)[0]; }
const GIRLX = track([[T.girl0, [-70]], [T.girl1, [230]], [T.girlStep0, [230]], [T.girlStep1, [320]], [60, [320]]]);
// pigtail pendulum, pre-simulated (deterministic)
const SWING = (() => {
  const dt = 1 / 120, n = Math.ceil(DUR / dt) + 2, out = new Float32Array(n); let phi = 0, om = 0, px = null, vx = 0;
  for (let i = 0; i < n; i++) { const t = i * dt, x = GIRLX(t)[0], v = px == null ? 0 : (x - px) / dt, a = (v - vx) / dt; px = x; vx = v; om += (-40 * phi - 4 * om - .0022 * clamp(a, -5000, 5000)) * dt; phi += om * dt; out[i] = clamp(phi, -.9, .9); }
  return t => out[clamp(Math.round(t * 120), 0, n - 1)];
})();

function grandmaPose(t) {
  if (t < T.press) return null;
  const P = { ...GM };
  // lean (rot) and head over time
  const K = track([[2.6, [.55, .1]], [6.2, [.55, .1]], [6.7, [.2, -.12]], [8.8, [.2, -.08]], [9.3, [.45, .1]], [11.0, [.45, .1]], [11.3, [.15, -.1]], [13.4, [.15, -.08]],
    [13.8, [.18, .12]], [15.6, [.18, .12]], [16.2, [.08, -.12]], [17.6, [.08, -.1]], [18.2, [.02, -.38]], [21.4, [.02, -.36]], [22.0, [.2, -.05]], [22.9, [.34, .02]], [24.9, [.34, .05]],
    [25.4, [.22, .14]], [26.8, [.22, .1]], [29.6, [.18, -.05]]])(t);
  P.rot = K[0]; P.head = K[1] + talk('g1', t, 1) + talk('g2', t, 2) + talk('g3', t, 3);
  const [tx, ty, tr0] = tremor(t, 11); P.x += tx; P.y += ty; P.rot += tr0;
  // hands: pat the soil / rest on knee / point up at the old palm / rest on Appu's head
  const patting = (t < 6.3) || (t > 9.1 && t < 11.1);
  const patY = GY - 22 - Math.abs(Math.sin(t * 7.5)) * 16;
  const knee = W2(P, 74, 26);
  const appuHead = [appuBoyX(t) - 4, GY - (132 + 118 + 64 * 1.3) * .82];        // crown of the boy's head
  let tgt = patting ? [640 + Math.sin(t * 1.3) * 18, patY] : knee;
  const pt = E(t, 17.9, 18.5) * (1 - E(t, 21.3, 21.9));
  if (pt > 0) tgt = [lerp(tgt[0], 420, pt), lerp(tgt[1], 930, pt)];
  const hp = E(t, T.headPat - .4, T.headPat) * (1 - E(t, T.headPat1, T.headPat1 + .5));
  if (hp > 0) tgt = [lerp(tgt[0], appuHead[0] + 6, hp), lerp(tgt[1], appuHead[1] + Math.sin(t * 4) * 3 * hp, hp)];
  if (!patting && pt === 0 && hp === 0 && t > 6.3) { const u = E(t, 6.3, 6.8) * (t < 9.1 ? 1 : E(t, 11.1, 11.6)); tgt = [lerp(640, knee[0], u), lerp(patY, knee[1], u)]; }
  P.aF = { to: tgt, bend: -1 };
  P.aB = { to: W2(P, 52, 30), bend: -1 };
  return P;
}
function appuPose(t) {
  if (t < T.run0) return null;
  const C = CAST;
  if (t < 30.0) {                                   // the boy
    const P = { fig: C.boy, x: appuBoyX(t), sc: .82, dir: 1, rot: 0, head: 0 };
    P.y = GY - (118 + 12 + 2) * P.sc;
    let legA = 0;
    if (t < T.run1) { const ph = (t - T.run0) * 11; legA = Math.sin(ph) * .5; P.y -= Math.abs(Math.sin(ph)) * 8; P.rot = .1; }
    else if (t < T.freeze) { const u = seg(t, T.run1, T.freeze); P.y -= Math.sin(u * Math.PI) * 30; legA = -.25 * Math.sin(u * Math.PI); }
    else if (t > T.walk0 && t < T.walk1) { const ph = (t - T.walk0) * 7; legA = Math.sin(ph) * .3; P.y -= Math.abs(Math.sin(ph)) * 4; }
    else legA = -.12 + .14 * E(t, T.freeze, T.freeze + .25) * (1 - E(t, T.freeze + 1, T.freeze + 1.4));   // freeze pose: feet apart
    P.lF = -legA - .08; P.lB = legA + .08;
    const K = track([[T.run0, [.1, 0]], [6.3, [-.04, -.12]], [7.4, [-.02, -.05]], [8.9, [0, -.1]], [11.2, [0, .02]], [13.4, [0, .02]], [13.8, [.1, -.08]], [15.7, [.08, -.06]],
      [16.2, [0, 0]], [18.0, [0, 0]], [18.7, [-.04, -.42]], [21.0, [-.04, -.4]], [21.9, [.04, .12]], [24.9, [.04, .14]], [25.4, [.1, .2]], [26.8, [.06, .12]], [27.6, [0, -.2]]])(t);
    P.rot += K[0]; P.head = K[1] + talk('a1', t, 4) + talk('a2', t, 5) + talk('a3', t, 6);
    const [tx, ty, tr0] = tremor(t, 22, t > T.freeze && t < T.freeze + 1 ? .4 : 1); P.x += tx; P.y += ty; P.rot += tr0;
    // front hand holds the tender coconut
    let hand = [P.x + 34, P.y - 74 * P.sc];
    if (t > 6.05 && t < 6.9) hand = [P.x + 46, P.y - 108 * P.sc - 10 * E(t, 6.05, 6.3)];
    if (t > 13.6 && t < 15.8) { const u = E(t, 13.6, 14.1) * (1 - E(t, 15.3, 15.8)); hand = [lerp(hand[0], P.x + 66, u), lerp(hand[1], P.y - 100 * P.sc, u)]; }
    let crot = 0;
    if (t > T.pour0) { const u = E(t, T.pour0, T.pour0 + .5) * (1 - E(t, T.pour1, T.pour1 + .5)); hand = [lerp(hand[0], SAP1 - 22, u), lerp(hand[1], GY - 128, u)]; crot = 1.85 * E(t, T.pour0 + .3, T.pour0 + .8) * (1 - E(t, T.pour1, T.pour1 + .4)); }
    P.aF = { to: hand, bend: 1 };
    P.prop = { pc: C.ilaneer, at: [2, 34], rot: crot };
    // back hand: gestures on his questions, otherwise hangs
    let bh = [P.x - 16, P.y - 20 * P.sc];
    const g1 = E(t, 6.6, 7.0) * (1 - E(t, 8.4, 8.8)), g2 = E(t, 9.0, 9.4) * (1 - E(t, 10.7, 11.1));
    if (g1) bh = [lerp(bh[0], P.x + 90, g1), lerp(bh[1], P.y + 20, g1)];
    if (g2) bh = [lerp(bh[0], P.x + 70, g2), lerp(bh[1], P.y - 70, g2)];
    P.aB = { to: bh, bend: 1 };
    P.pourU = t > T.pour0 ? E(t, T.pour0 + .5, T.pour0 + .8) * (1 - E(t, T.pour1, T.pour1 + .3)) : 0;
    return P;
  }
  if (t < 31.6) {                                   // young man (piece swap)
    const P = { fig: C.man, x: 430, sc: .98, dir: 1, rot: 0, head: -.12 + Math.sin(t * .8) * .03 }; P.y = GY - (162 + 2 + 2) * P.sc;
    const [tx, ty, tr0] = tremor(t, 31); P.x += tx; P.y += ty; P.rot += tr0;
    P.aF = { to: [P.x + 30, P.y + 10], bend: 1 }; P.aB = { to: [P.x - 10, P.y + 14], bend: 1 }; P.lF = -.05; P.lB = .06;
    return P;
  }
  if (t < T.oldRekneel) {                           // old man standing with a stick, looking up at the grown palm
    const P = { fig: C.oldStand, x: 410, sc: .98, dir: 1, rot: .08, head: -.32 * E(t, 33.6, 34.4) + Math.sin(t * .7) * .02 }; P.y = GY - (162 + 4) * P.sc;
    const [tx, ty, tr0] = tremor(t, 41, 1.3); P.x += tx; P.y += ty; P.rot += tr0;
    P.aF = { to: [P.x + 52, P.y - 10], bend: 1 }; P.aB = { to: [P.x - 8, P.y + 12], bend: 1 }; P.lF = -.06; P.lB = .08;
    P.prop = { pc: C.stick, at: [2, 8], vertical: true };
    return P;
  }
  // old man kneels at the new sapling (re-pressed), facing left — echo of Ammumma
  const P = { fig: C.oldKneel, x: 470, sc: 1.22, dir: -1 }; P.y = GY - 74 * P.sc;
  const K = track([[35.35, [.5, .1]], [38.9, [.5, .1]], [39.3, [.16, -.12]], [41.3, [.24, -.06]], [44, [.24, -.04]]])(t);
  P.rot = K[0]; P.head = K[1] + talk('p1', t, 7);
  const [tx, ty, tr0] = tremor(t, 51); P.x += tx; P.y += ty; P.rot += tr0;
  const patting = t < 39.0, patY = GY - 22 - Math.abs(Math.sin(t * 6.8)) * 14;
  const knee = W2(P, 74, 26);
  let tgt = patting ? [SAP2 + 36 + Math.sin(t * 1.1) * 14, patY] : knee;
  if (!patting) { const u = E(t, 39.0, 39.4); tgt = [lerp(SAP2 + 36, knee[0], u), lerp(patY, knee[1], u)]; }
  const hp = E(t, T.oldPat - .4, T.oldPat);
  const gx = GIRLX(t)[0];
  if (hp > 0) { const gh = [gx - 4, GY - (122 + 118 + 64 * 1.34) * .8]; tgt = [lerp(tgt[0], gh[0] + 6, hp), lerp(tgt[1], gh[1] + Math.sin(t * 4) * 3 * hp, hp)]; }
  P.aF = { to: tgt, bend: -1 }; P.aB = { to: W2(P, 52, 30), bend: -1 };
  return P;
}
function girlPose(t) {
  if (t < T.girl0) return null;
  const P = { fig: CAST.girl, x: GIRLX(t)[0], sc: .8, dir: 1, rot: 0, head: 0 }; P.y = GY - (114 + 6 + 2) * P.sc;
  let legA = 0;
  if (t < T.girl1) { const ph = (t - T.girl0) * 12; legA = Math.sin(ph) * .4; P.y -= Math.abs(Math.sin(ph)) * 7; P.rot = .08; }
  else if (t > T.girlStep0 && t < T.girlStep1) { const ph = (t - T.girlStep0) * 8; legA = Math.sin(ph) * .25; P.y -= Math.abs(Math.sin(ph)) * 3; }
  P.lF = -legA - .04; P.lB = legA + .04;
  const K = track([[35.9, [.08, 0]], [36.6, [0, -.08]], [38.8, [0, -.06]], [39.4, [0, -.16]], [40.4, [0, .06]], [44, [0, .04]]])(t);
  P.rot += K[0]; P.head = K[1] + talk('m1', t, 8);
  const [tx, ty, tr0] = tremor(t, 61); P.x += tx; P.y += ty; P.rot += tr0;
  const pt = E(t, 36.8, 37.2) * (1 - E(t, 38.5, 38.9));
  P.aF = { to: [lerp(P.x + 18, SAP2 - 6, pt), lerp(P.y + 10, GY - 120, pt)], bend: 1 };
  P.aB = { to: [P.x - 14, P.y + 12], bend: 1 };
  P.swing = SWING(t);
  return P;
}

// ================= Camera =================
const KEYS = {
  press: track([[2.6, [540, 960, 1.04]], [2.6 + 4 / 24, [620, 1040, 1.36]], [2.95, [620, 1040, 1.3]], [3.6, [620, 1040, 1.3]], [6.4, [585, 1090, 1.48]]]),
  two: track([[6.4, [585, 1090, 1.48]], [13.5, [585, 1090, 1.5]], [14.6, [592, 1098, 1.62]], [15.9, [592, 1098, 1.62]]]),
  answer: track([[15.9, [592, 1098, 1.62]], [16.4, [450, 1060, 2.6]], [18.2, [452, 1060, 2.68]], [19.6, [300, 1180, 1.9]], [21.5, [280, 560, 1.9]], [21.7, [290, 600, 1.88]]]),
  close: track([[21.7, [290, 600, 1.88]], [22.4, [610, 1095, 1.9]], [24.9, [612, 1095, 1.86]], [26.8, [600, 1060, 1.68]]]),
  echo: track([[35.6, [540, 960, 1]], [36.7, [420, 1080, 1.48]], [41.3, [420, 1080, 1.6]]]),
  end: track([[41.3, [420, 1080, 1.6]], [44.6, [540, 980, .74]], [52, [540, 975, .72]]])
};
function camRaw(t) {
  const [, , n] = shotAt(t);
  if (n === 'open') return [540, 960, lerp(1, 1.04, E(t, 0, 2.6))];
  if (n === 'years') return [540, 960, 1];
  const k = KEYS[n]; return k(t);
}
function camAt(t) { const c = camRaw(t); if (c[2] >= 1) { c[0] = clamp(c[0], 540 / c[2], 1080 - 540 / c[2]); c[1] = clamp(c[1], 960 / c[2], 1920 - 960 / c[2]); } return c; }
const camM = ([cx, cy, z]) => [z, 0, 0, z, 540 - cx * z, 960 - cy * z];

// ================= Subtitles =================
const SUBTEXT = { g2: [['ഇപ്പൊ നീ കുടിച്ച ഈ ഇളനീരില്ലേ...', 'This tender coconut you just drank...'], ['അത് എന്റെ അമ്മൂമ്മ നട്ട തെങ്ങിലെയാ.', '...it came from a tree my grandma planted.']] };
const SUBS = [];
LINES.forEach((l, i) => {
  const d = dur(l.id), nxt = LINES[i + 1], tx = TEXT.find(x => x.id === l.id) || { text: '', en: '' };
  let end = l.t + Math.max(1.8, d + .6); if (nxt) end = Math.min(end, nxt.t - .12); else end = Math.min(end, T.title0 - .1);
  if (SPLIT[l.id] != null) { const m = l.t + SPLIT[l.id]; SUBS.push({ t0: l.t, t1: m + .05, ml: SUBTEXT[l.id][0][0], en: SUBTEXT[l.id][0][1] }); SUBS.push({ t0: m + .05, t1: end, ml: SUBTEXT[l.id][1][0], en: SUBTEXT[l.id][1][1] }); }
  else SUBS.push({ t0: l.t, t1: end, ml: tx.text, en: tx.en });
});
window.SUBS = SUBS;

// ================= One frame =================
const FIGS = [];
function drawScreen(t, C) {
  tr.setTransform(1, 0, 0, 1, 0, 0); tr.fillStyle = '#fff'; tr.fillRect(0, 0, W, H);
  const k = C[0], open = t < T.press;
  const revealU = E(t, T.curtainOff, T.curtainOff + .9);
  if (t >= T.curtainOff - .05) {
    // sky pieces
    if (!night(t)) { tr.save(); tr.globalCompositeOperation = 'multiply'; set(tr, mul(C, mul(Tm(860, 380 + Math.sin(t * .5) * 3), Rm(t * .03)))); drawPiece(tr, SC.sun); tr.restore(); }
    else { tr.save(); tr.globalCompositeOperation = 'multiply'; set(tr, mul(C, Tm(860, 380))); drawPiece(tr, SC.moon); tr.restore(); }
    if (t > 3 && t < 9.5) for (let b = 0; b < 2; b++) {
      const u = seg(t, 3 + b * .6, 9.5), x = lerp(1180, -120, u), y = 520 + b * 40 + Math.sin(u * 9 + b) * 14;
      tr.save(); tr.globalCompositeOperation = 'multiply'; set(tr, mul(C, mul(Tm(x, y), Sm(-.8)))); drawPiece(tr, SC.bird[Math.floor(t * 12 + b) % 2]); tr.restore();
    }
    // old palm (left), house (right), ground
    drawPalm(tr, C, OLDPALM, 215, t, { wind: t > 18 && t < 22 ? 1 : .3 });
    tr.save(); tr.globalCompositeOperation = 'multiply'; set(tr, mul(C, mul(Tm(1010, GY + 2), Sm(.8)))); drawPiece(tr, SC.house); tr.restore();
    tr.save(); tr.globalCompositeOperation = 'multiply'; set(tr, mul(C, Tm(0, GY))); drawPiece(tr, SC.ground); tr.restore();
    // sapling 1 → palm (piece swaps on the beat)
    let st = 0; T.swaps.forEach((s, i) => { if (t >= s) st = i + 1; });
    const sw = st ? T.swaps[st - 1] : 0, pop = st ? 1 + .07 * (1 - eo(seg(t, sw, sw + .3))) : 1, shake = st ? Math.sin((t - sw) * 40) * .02 * (1 - seg(t, sw, sw + .35)) : 0;
    if (t >= T.press) {
      const pr = eo(seg(t, T.press, T.press + .5));
      if (st === 0 || t < 30) { tr.save(); tr.globalCompositeOperation = 'multiply'; set(tr, mul(C, Tm(SAP1, GY + 2))); drawPiece(tr, SC.mound); tr.restore(); }
      drawPalm(tr, mul(C, mul(Tm(SAP1, GY), mul(Rm(shake), Tm(-SAP1, -GY)))), GROW[st], SAP1, t, { sc: pop * (st ? 1 : .72), alpha: .35 + .65 * pr, blur: (1 - pr) * 30 * k, wind: st > 2 ? .6 : 0 });
    }
    if (t >= T.sprout2) {
      const pr = eo(seg(t, T.sprout2, T.sprout2 + .5));
      tr.save(); tr.globalCompositeOperation = 'multiply'; tr.globalAlpha = pr; set(tr, mul(C, Tm(SAP2, GY + 2))); drawPiece(tr, SC.mound); tr.restore();
      drawPalm(tr, C, SPROUT, SAP2, t, { sc: .62 * (1 + (1 - pr) * 1.4), alpha: .35 + .65 * pr, blur: (1 - pr) * 30 * k });
    }
  }
  // performers
  const rods = [];
  const gp = grandmaPose(t);
  if (gp) { const r = drawFigure(tr, C, CAST.grandma, gp, { press: eo(seg(t, T.press, T.press + .55)), lift: seg(t, T.liftGrandma, T.liftGrandma + 1.0) }); if (r && t < T.liftGrandma) rods.push(r.rods[0], r.rods[1]); }
  const ap0 = appuPose(t);
  if (ap0) {
    let press = 1, lift = 0;
    if (ap0.fig === CAST.man) press = eo(seg(t, 30.0, 30.3));
    if (ap0.fig === CAST.oldStand) { press = eo(seg(t, 31.6, 31.9)); lift = seg(t, T.oldRekneel - .3, T.oldRekneel); }
    if (ap0.fig === CAST.oldKneel) press = eo(seg(t, T.oldRekneel, T.oldRekneel + .45));
    const r = drawFigure(tr, C, ap0.fig, ap0, { press, lift });
    if (r) { rods.push(r.rods[0], r.rods[1]);
      if (ap0.pourU > 0) {            // water from the tender coconut onto the sapling
        const mouth = ap(mul(r.F.Mh, mul(Tm(2, 34), Rm(ap0.prop.rot))), 10, -36);
        for (let i = 0; i < 7; i++) {
          const ph = ((t * 1.9 + i / 7) % 1), wy = mouth[1] + ph * ph * 150 * k, wx = mouth[0] - ph * 6 * k;
          tr.save(); tr.globalCompositeOperation = 'multiply'; tr.globalAlpha = ap0.pourU * (1 - ph * .4); tr.setTransform(k * .9, 0, 0, k * .9, wx, wy); drawPiece(tr, CAST.drop); tr.restore();
        }
      }
    }
  }
  const girl = girlPose(t);
  if (girl) { const r = drawFigure(tr, C, CAST.girl, girl, { press: eo(seg(t, T.girl0, T.girl0 + .3)) }); if (r) rods.push(r.rods[0], r.rods[1]); }
  if (rods.length) drawRods(tr, rods, rods.map((q, j) => [q[0] - (j % 2 ? 40 : 90) * k, q[1] + 1500 * k]), 2.2 * k, .55);
  // title plaque on two rods
  if (t >= T.title0) {
    const pr = eo(seg(t, T.title0, T.title1)), sc = 1.0 * (1 + (1 - pr) * 1.5), y = 1640 + Math.sin(t * 1.2) * 4;
    tr.save(); tr.globalCompositeOperation = 'multiply'; tr.globalAlpha = .35 + .65 * pr; if (pr < 1) tr.filter = `blur(${((1 - pr) * 30 * k).toFixed(1)}px)`;
    set(tr, mul(C, mul(Tm(540, y), Sm(sc)))); drawPiece(tr, PLQ); tr.restore();
    if (pr > .9) { const r = [[-330, 175], [330, 175]].map(([a, b]) => ap(C, 540 + a * sc, y + b * sc)); drawRods(tr, r, r.map(p => [p[0] - 30 * k, p[1] + 1600 * k]), 2.2 * k, .6); }
  }
  // the opening curtain: dark hide with one carved hole; lifted off the cloth
  if (t < T.curtainOff + 1.0) {
    const u = seg(t, T.curtainOff, T.curtainOff + 1.0), sc = 1 + u * .9;
    tr.save(); tr.globalCompositeOperation = 'multiply'; tr.globalAlpha = 1 - ei(u); if (u > 0) tr.filter = `blur(${(u * 30 * k).toFixed(1)}px)`;
    set(tr, mul(C, mul(Tm(540, 1060), mul(Sm(sc), Tm(-540, -1060))))); drawPiece(tr, SC.curtain); tr.restore();
  }
}

function render(t) {
  fr.setTransform(1, 0, 0, 1, 0, 0); fr.clearRect(0, 0, W, H); fr.globalAlpha = 1; fr.filter = 'none';
  if (qs.get('test') === 'model') return modelSheet();
  const cam = camAt(t), C = camM(cam), L = lamps(t), nEff = L.reduce((a, l) => a + l[2], 0);
  drawScreen(t, C);
  if (cam[2] < 1.02) drawFrame(fr, C, clamp(nEff, 0, 3) / 2);
  drawSubs(t);
  const o = { lamps: L, cam, rect: [0, 0, 1080, 1920], sigB: 760, sigC: 130, amb: .3, time: t, vign: .45, sat: 1.1, contrast: .15, bloom: .3,
    expo: 1.4 / Math.sqrt(Math.max(1, nEff)) * (nEff < .05 ? 0 : 1) };
  if (t < T.lamp2 + .2) o.bloom = .45;
  GL.render(trc, frc, o);
}
function drawSubs(t) {
  if (qs.get('nosub')) return;
  for (const s of SUBS) if (t >= s.t0 && t < s.t1) { const a = Math.min(E(t, s.t0, s.t0 + .18), 1 - E(t, s.t1 - .2, s.t1)); drawSub(fr, s.ml, s.en, a, 1 - eo(seg(t, s.t0, s.t0 + .22))); }
}
// model sheet: the cast on one lit cloth, at 1.6×
function modelSheet() {
  tr.setTransform(1, 0, 0, 1, 0, 0); tr.fillStyle = '#fff'; tr.fillRect(0, 0, W, H);
  const C = [1, 0, 0, 1, 0, 0], g = tr;
  const row1 = 760, row2 = 1500;
  drawFigure(g, C, CAST.grandma, { x: 260, y: row1 - 74 * 1.25, sc: 1.25, dir: -1, rot: .2, aF: { to: [120, row1 - 30], bend: -1 }, aB: { to: [190, row1 - 50], bend: -1 } });
  drawFigure(g, C, CAST.boy, { x: 560, y: row1 - 132 * .82, sc: .82, dir: 1, lF: -.1, lB: .1, aF: { to: [600, row1 - 200], bend: 1 }, aB: { to: [540, row1 - 100], bend: 1 }, prop: { pc: CAST.ilaneer, at: [2, 34], rot: 0 } });
  drawFigure(g, C, CAST.girl, { x: 860, y: row1 - 122 * .8, sc: .8, dir: 1, lF: -.05, lB: .05, aF: { to: [890, row1 - 110], bend: 1 }, aB: { to: [845, row1 - 90], bend: 1 }, swing: .2 });
  drawFigure(g, C, CAST.man, { x: 200, y: row2 - 166 * .98, sc: .98, dir: 1, aF: { to: [230, row2 - 150], bend: 1 }, aB: { to: [190, row2 - 150], bend: 1 } });
  drawFigure(g, C, CAST.oldStand, { x: 520, y: row2 - 166 * .98, sc: .98, dir: 1, rot: .08, aF: { to: [560, row2 - 190], bend: 1 }, aB: { to: [510, row2 - 150], bend: 1 }, prop: { pc: CAST.stick, at: [2, 8], vertical: true } });
  drawFigure(g, C, CAST.oldKneel, { x: 880, y: row2 - 74 * 1.22, sc: 1.22, dir: -1, rot: .3, aF: { to: [760, row2 - 30], bend: -1 }, aB: { to: [830, row2 - 50], bend: -1 } });
  drawPalm(g, C, GROW[2], 700, 0, { y: 1880 });
  GL.render(trc, frc, { lamps: [[540, 700, 1, .9], [540, 1400, 1, .9]], cam: [540, 960, 1], rect: [0, 0, 1080, 1920], sigB: 900, sigC: 200, amb: .4, expo: 1.4, vign: .3, sat: 1.1, contrast: .12, bloom: .25 });
}

// ================= Events for the mix =================
function events() {
  const ev = [], add = (type, t, o = {}) => ev.push({ type, t: +t.toFixed(3), ...o });
  add('room', 0, { d: DUR });
  add('ignite', T.lamp0, { v: .7 }); add('ignite', T.lamp1, { v: .5 }); add('ignite', T.lamp2, { v: .5 });
  add('liftoff', T.curtainOff); add('drum', T.press, { v: 1 }); add('cymbal', T.press, { v: .7 }); add('rodtap', T.press + .05);
  add('birds', 2.8, { d: 7.5 }); add('breeze', 2.6, { d: 13.3 });
  for (let k = 0; k < 11; k++) add('step', T.run0 + .1 + k * (T.run1 - T.run0 - .1) / 11, { v: .45 + .25 * (k % 2) });
  add('hop', T.hop); add('land', T.freeze); add('woodblock', T.freeze, { v: 1 });
  // soil pats while patting
  for (let t = 2.8; t < 6.3; t += 2 * Math.PI / 7.5 / 2) add('pat', t + .21, { v: .5 });
  for (let t = 9.2; t < 11.1; t += 2 * Math.PI / 7.5 / 2) add('pat', t + .21, { v: .4 });
  add('slosh', 6.1, { v: .5 }); add('slosh', 13.8, { v: .5 });
  add('cut', T.pushClose); add('woodblock', T.tap, { v: .7 }); add('fronds', 18.2, { d: 3.6 }); add('breeze', 16.9, { d: 5.2, v: .7 });
  for (let k = 0; k < 7; k++) add('step', T.walk0 + .15 + k * .24, { v: .3 });
  add('pour', T.pour0 + .5, { d: T.pour1 - T.pour0 - .2 });
  add('scrape', T.scrape);
  T.swaps.forEach((s, i) => { add('snuff', s - .75, { v: .6 }); add('swap', s); add('drum', s, { v: .8 + i * .05 }); add('ignite', s, { v: .45 }); if (i < 4) add('cymbal', s + .02, { v: .4 }); });
  add('liftoff', T.liftGrandma); add('swap', 31.6, { v: .6 });
  add('gong', T.bigGong, { v: 1, fall: 1 });
  add('liftoff', T.oldRekneel - .3, { v: .6 }); add('rodtap', T.oldRekneel + .1); add('rodtap', T.sprout2 + .05, { v: .6 });
  add('birds', 35.8, { d: 5, v: .5 });
  for (let k = 0; k < 6; k++) add('step', T.girl0 + .05 + k * .09, { v: .35 });
  add('land', T.girl1, { v: .5 });
  for (let t = 35.6; t < 39.0; t += 2 * Math.PI / 6.8 / 2) add('pat', t + .23, { v: .35 });
  for (let k = 0; k < 3; k++) add('step', T.girlStep0 + .1 + k * .25, { v: .3 });
  add('cloth', T.pull0, { d: 2.5 });
  add('heartbeat', 42.0, { d: 3.6 });
  add('gong', T.title0 + .1, { v: .55, rise: 1 }); add('rodtap', T.title1, { v: .9 });
  add('carry', T.carry0, { d: T.carry1 - T.carry0 }); add('snuff', T.carry1 - .1, { v: .7 }); add('stop', T.stop);
  for (const l of LINES) add('vo', l.t, { id: l.id, who: l.who });
  return ev.sort((a, b) => a.t - b.t);
}
window.EV = events(); window.T = T; window.DUR = DUR; window.render = render;
window.TEXTS = t => {
  if (t < T.title0 || t >= T.carry0 + .8) return [];
  const cam = camAt(t), C = camM(cam), sc = 1.0, a = ap(C, 540 - 420 * sc, 1640 - 190 * sc), b = ap(C, 540 + 420 * sc, 1640 + 190 * sc);
  return [{ id: 'title', text: 'തെങ്ങിൻതൈ THE COCONUT SAPLING', x0: a[0], y0: a[1], x1: b[0], y1: b[1] }];
};
render(parseFloat(qs.get('t') ?? '12'));
window.READY = true;
