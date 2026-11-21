// The puppets of "Thengin Thai": Ammumma, Appu (boy → young man → old man), Minnu.
// Every figure faces right in its own space (flip with pose.dir = −1). Origin = waist. Units: cloth px at figure scale 1.
// Sympathetic figures throughout, so every face is open-cut: features are thin strips of hide around a hole.
import { piece, fill, cut, cutLine, ink, within, smooth, poly, lattice, coin, beads, beadLine, meander, cloud, scalesOpen, DYE } from './carve.js';

export const KD = {                     // Kerala dye set (transmitted light): vermilion, ochre/gold, malachite, jade + raw hide + ink
  ...DYE, skin: '#e2aa64', mundu: '#dcbd7c', mundu2: '#c99a52', kasavu: '#b8720e', grey: '#5a5048', shirtG: '#1d6438', shirtO: '#bf5f12', blouse: '#a94e10',
  pavada: '#a51c16', earth: '#8a5a2c', husk: '#94571f', leaf: '#23703a', leaf2: '#2f8040', water: '#1f4d7a'
};
const J0 = { neck: [4, -118], shF: [6, -104], shB: [-4, -106], rod: [4, -110], hipF: [8, 2], hipB: [-6, 2] };
const UA = 56, FA = 50, HAND = 12;

// ———————————————————— heads ————————————————————
// profile points (neck pivot at 0,0): chin → lips → nose → brow → forehead
const PROF = [[6, 4], [10, -4], [16, -9], [18, -13], [15.5, -15.5], [19, -18], [18.5, -21.5], [25, -27], [19.5, -36], [20.5, -42], [18, -54], [11, -64]];
function headPiece(o) {
  const K = o.k || 1;
  return piece([-56 * K, -112 * K, 40 * K, 14 * K], g => {
    g.scale(K, K);
    const hairIn = o.hairIn || [[11, -64], [4, -57], [-2, -48], [-4, -36], [-6, -22], [-11, -9]];
    const back = o.hairOut || [[-11, -9], [-22, -16], [-29, -34], [-29, -52], [-20, -68], [-6, -76], [8, -72], [14, -66]];
    // jaw strip and neck front (the open face is bounded by the profile, the jaw and the hair)
    ink(g, 2.6, q => poly(q, PROF, false));
    ink(g, 2.2, q => { q.moveTo(-11, -9); q.quadraticCurveTo(0, -2, 10, -4); });
    // eye, brow, mouth, nostril, cheek
    ink(g, 1.6, q => { q.moveTo(8.5, -39); q.quadraticCurveTo(12, -41.5, 15.5, -39.2); });
    ink(g, 1.1, q => { q.moveTo(9, -38.6); q.quadraticCurveTo(12, -37.4, 15, -38.9); });
    g.beginPath(); g.arc(13, -39.3, 1.5, 0, 7); g.fillStyle = DYE.ink; g.fill();
    ink(g, 1.8, q => { q.moveTo(6.5, -45.5); q.quadraticCurveTo(12, -48, 18, -45); }, o.browCol || DYE.ink);
    ink(g, 1.2, q => { q.moveTo(17, -17.2); q.lineTo(12.5, -16.4); });
    ink(g, 1, q => { q.moveTo(20.5, -24.6); q.quadraticCurveTo(18.5, -25.5, 18.4, -23.6); });
    if (o.wrinkles) {
      ink(g, .9, q => { q.moveTo(15.5, -24); q.quadraticCurveTo(10.5, -20, 11.5, -13.5); });
      ink(g, .8, q => { q.moveTo(5, -38); q.lineTo(2, -36.5); q.moveTo(5, -40); q.lineTo(1.8, -40.2); });
      ink(g, .8, q => { q.moveTo(6, -55); q.quadraticCurveTo(11, -57, 15, -55.5); });
    }
    if (o.smile) ink(g, 1, q => { q.moveTo(12, -14.5); q.quadraticCurveTo(14.5, -13, 16.5, -15.5); });
    // ear
    const ear = q => smooth(q, [[-6, -27], [-2, -30], [-1.5, -38], [-5, -41], [-9, -36], [-9, -29]]);
    fill(g, o.skin || KD.skin, ear); cutLine(g, 1, q => { q.moveTo(-4, -37); q.quadraticCurveTo(-7, -33, -4.5, -30); }); ink(g, 1.3, ear);
    if (o.earring) { g.beginPath(); g.arc(-4.5, -24, 3.6, 0, 7); g.fillStyle = KD.kasavu; g.fill(); cut(g, q => q.arc(-4.5, -24, 1.5, 0, 7)); ink(g, 1, q => q.arc(-4.5, -24, 3.6, 0, 7)); }
    // hair (solid, with combed slits)
    const hair = q => { q.moveTo(...hairIn[0]); for (const pt of hairIn.slice(1)) q.lineTo(...pt); smoothTail(q, back); };
    fill(g, o.hair || DYE.ink, hair, 'nonzero');
    within(g, hair, () => { for (let k = 0; k < 9; k++) cutLine(g, .75, q => { q.moveTo(8 - k * 3.4, -70 + k * .5); q.quadraticCurveTo(-22 + k * .6, -56 + k * 2.4, -16 - k * .4, -16 + k * .8); }); });
    ink(g, 1.4, hair);
    if (o.bun) {   // Ammumma's knot at the back of the head
      const bun = q => q.arc(-30, -54, 12.5, 0, 7);
      fill(g, o.hair, bun); cut(g, q => { q.arc(-30, -54, 5.4, 0, 7); }); cutLine(g, .9, q => { q.arc(-30, -54, 9, 2.4, 5.6); }); ink(g, 1.4, bun);
      ink(g, 1.6, q => { q.moveTo(-41, -50); q.lineTo(-19, -60); }, KD.kasavu);       // a pin
    }
    if (o.fringe) fill(g, DYE.ink, q => smooth(q, [[11, -64], [17, -60], [14, -55], [8, -56], [3, -52], [0, -60]]));
    if (o.tache) { const m = q => smooth(q, [[19, -20.4], [13, -21.4], [8, -19.2], [9, -17.4], [14, -18.8], [19.5, -18.6]]); fill(g, o.tacheCol || DYE.ink, m); ink(g, .8, m); }
    if (o.glasses) {
      ink(g, 1.6, q => { q.ellipse(13, -39.5, 6.6, 5.4, 0, 0, 7); });
      ink(g, 1.4, q => { q.moveTo(6.4, -40); q.lineTo(-3, -38); });
    }
    if (o.jasmine) { beads(g, [[-18, -70], [-24, -66], [-28, -60], [-31, -53]], 2.6); }
  }, { seed: o.seed || 3 });
}
function smoothTail(q, pts) { for (let i = 0; i < pts.length - 1; i++) { const m = [(pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2]; q.quadraticCurveTo(pts[i][0], pts[i][1], m[0], m[1]); } q.lineTo(...pts[pts.length - 1]); q.closePath(); }

// ———————————————————— arms ————————————————————
function upperArm(col, opt = {}) {
  return piece([-14, -10, 14, UA + 10], g => {
    const s = q => smooth(q, [[-10, -6], [0, -11], [10, -6], [9, UA * .5], [7, UA + 4], [0, UA + 8], [-7, UA + 4], [-9, UA * .5]]);
    fill(g, col, s);
    if (opt.sleeve != null) {   // sleeve stops at opt.sleeve, skin below
      within(g, s, () => { g.fillStyle = opt.skin || KD.skin; g.fillRect(-14, opt.sleeve, 28, 80); });
      ink(g, 1.2, q => { q.moveTo(-9.5, opt.sleeve); q.lineTo(9.5, opt.sleeve); });
      within(g, s, () => { if (opt.puff) cutLine(g, 1, q => { for (let k = 0; k < 3; k++) { q.moveTo(-6 + k * 6, -4); q.quadraticCurveTo(-5 + k * 6, opt.sleeve * .5, -6 + k * 6, opt.sleeve - 3); } });
        else beadLine(g, -5, opt.sleeve - 5, 5, opt.sleeve - 5, 1.3, 5); });
    } else within(g, s, () => lattice(g, -10, 2, 10, UA, 8, 1.8));
    ink(g, 1.6, s);
  }, { seed: 11 });
}
function foreArm(opt = {}) {
  return piece([-14, -10, 18, FA + HAND + 12], g => {
    const s = q => smooth(q, [[-8, -6], [0, -9], [8, -6], [6.5, FA * .6], [6, FA], [-5, FA], [-6.5, FA * .6]]);
    fill(g, opt.skin || KD.skin, s); ink(g, 1.5, s);
    // hand: mitten pointing down, thumb forward
    const h = q => smooth(q, [[-6, FA - 3], [7, FA - 3], [13, FA + 4], [9, FA + 7], [7, FA + 9], [5, FA + HAND + 6], [-2, FA + HAND + 8], [-7, FA + HAND + 2], [-7, FA + 6]]);
    fill(g, opt.skin || KD.skin, h); cutLine(g, .8, q => { q.moveTo(-3, FA + 8); q.lineTo(-2, FA + HAND + 3); q.moveTo(1, FA + 8); q.lineTo(2, FA + HAND + 4); }); ink(g, 1.4, h);
    if (opt.bangles) for (let k = 0; k < opt.bangles; k++) { ink(g, 2.4, q => { q.moveTo(-6.4, FA - 9 - k * 4.5); q.lineTo(6.4, FA - 9 - k * 4.5); }, KD.kasavu); }
    if (opt.watch) { fill(g, DYE.ink, q => q.rect(-6.5, FA - 11, 13, 6)); cut(g, q => q.arc(0, FA - 8, 1.8, 0, 7)); }
  }, { seed: 12 });
}
function leg(len, opt = {}) {
  return piece([-16, -8, 30, len + 10], g => {
    const y0 = opt.feetOnly ? len - 40 : -4;
    const s = q => smooth(q, opt.feetOnly ? [[-7, y0], [7, y0], [6, len - 14], [-5, len - 14]] : [[-10, -4], [0, -8], [10, -4], [9, len * .5], [6, len - 14], [-5, len - 14], [-8, len * .5]]);
    fill(g, opt.skin || KD.skin, s); within(g, s, () => { cutLine(g, 1, q => { q.moveTo(-2, len * .52); q.quadraticCurveTo(2, len * .56, 4, len * .52); }); }); ink(g, 1.5, s);
    const f = q => smooth(q, [[-7, len - 16], [6, len - 16], [9, len - 6], [24, len - 4], [26, len + 2], [-8, len + 2]]);
    fill(g, opt.skin || KD.skin, f); ink(g, 1.4, f);
    if (opt.anklet) beadLine(g, -6, len - 13, 6, len - 13, 1.4, 3.6);
  }, { seed: 13 });
}

// ———————————————————— torsos and lower bodies ————————————————————
const TORSO0 = [[-20, 2], [-25, -40], [-26, -80], [-22, -104], [-12, -116], [-3, -121], [-2, -132], [10, -132], [11, -121], [22, -112], [28, -96], [29, -72], [25, -40], [21, 2]];
const TORSO = TORSO0.map(([x, y]) => [x * 1.22 + (y < -110 ? 0 : 1), y]);
function torso(o) {
  return piece([-40, -140, 46, 10], g => {
    const t = q => smooth(q, TORSO);
    fill(g, o.col, t);
    within(g, t, () => {
      g.fillStyle = o.skin || KD.skin; g.fillRect(-6, -140, 20, 18);                         // neck
      if (o.kind === 'shirt') {
        lattice(g, -26, -96, 30, -10, 11, 2.4);
        ink(g, 1.4, q => { q.moveTo(17, -114); q.lineTo(14, -4); });                            // placket
        for (let k = 0; k < 5; k++) coin(g, 18, -100 + k * 21, 3.4);
        fill(g, o.col2 || o.col, q => poly(q, [[-6, -122], [10, -121], [18, -110], [9, -106], [2, -116], [-8, -112]]));   // collar
        ink(g, 1.2, q => poly(q, [[-6, -122], [10, -121], [18, -110], [9, -106], [2, -116], [-8, -112]]));
        const pk = q => q.rect(-2, -86, 14, 14); ink(g, 1.2, pk);
      }
      if (o.kind === 'blouse') {   // Ammumma: blouse + neriyathu (shoulder cloth) with a gold kasavu border, across from back shoulder to front waist
        scalesOpen(g, -26, -100, 30, -40, 5.6);
        const band = q => poly(q, [[-24, -112], [-10, -120], [30, -30], [28, 4], [12, 4]]);
        fill(g, KD.mundu, band); within(g, band, () => { lattice(g, -24, -116, 32, 4, 9, 2); });
        fill(g, KD.kasavu, q => poly(q, [[-10, -120], [-5, -121], [30, -38], [30, -30]])); ink(g, 1, q => poly(q, [[-10, -120], [-5, -121], [30, -38], [30, -30]]));
        ink(g, 1.3, band);
      }
      if (o.kind === 'girl') {
        scalesOpen(g, -26, -100, 30, -10, 5.2);
        fill(g, KD.kasavu, q => q.rect(-30, -10, 64, 7)); within(g, q => q.rect(-30, -10, 64, 7), () => meander(g, -28, -4.5, 32, 2.6, .8));
      }
      if (o.kind === 'kurta') {
        lattice(g, -26, -110, 30, -6, 9, 1.6); ink(g, 1.2, q => { q.moveTo(14, -118); q.lineTo(13, -70); });
        for (let k = 0; k < 3; k++) coin(g, 16.5, -108 + k * 14, 2.8);
      }
    });
    ink(g, 1.8, t);
  }, { seed: o.seed || 21 });
}
function shorts(col) {
  return piece([-32, -10, 34, 48], g => {
    const s = q => smooth(q, [[-22, -6], [24, -6], [27, 20], [26, 40], [2, 42], [-1, 30], [-4, 42], [-26, 40], [-25, 18]]);
    fill(g, col, s); within(g, s, () => { lattice(g, -26, 4, 28, 44, 9, 2); g.fillStyle = DYE.ink; g.fillRect(-26, -6, 54, 6); }); ink(g, 1.7, s);
  }, { seed: 31 });
}
function muduLong(len, col, kasavu = true) {     // mundu to the ankles
  return piece([-40, -12, 44, len + 8], g => {
    const s = q => smooth(q, [[-24, -8], [25, -8], [27, len * .4], [31, len - 2], [8, len + 3], [-30, len], [-28, len * .45]]);
    fill(g, col, s);
    within(g, s, () => {
      if (kasavu) { g.fillStyle = KD.kasavu; g.fillRect(-40, len - 16, 90, 9); meander(g, -36, len - 9.5, 40, 3, .9); }
      g.fillStyle = KD.kasavu; g.fillRect(14, -8, 7, len); cutLine(g, 1, q => { q.moveTo(17.5, 0); q.lineTo(18, len - 18); });
      for (let k = 0; k < 4; k++) cutLine(g, 1.3, q => { q.moveTo(-20 + k * 9, 14 + k * 3); q.quadraticCurveTo(-18 + k * 9, len * .5, -22 + k * 10, len - 22); });
      g.fillStyle = DYE.ink; g.globalAlpha = .55; g.fillRect(-28, -8, 56, 5); g.globalAlpha = 1;
    });
    ink(g, 1.7, s);
  }, { seed: 33 });
}
function pavada(len) {                       // girl's long skirt, flared, gold border
  return piece([-46, -12, 50, len + 8], g => {
    const s = q => smooth(q, [[-22, -8], [23, -8], [30, len * .45], [40, len], [0, len + 4], [-40, len], [-29, len * .45]]);
    fill(g, KD.pavada, s);
    within(g, s, () => {
      lattice(g, -40, 6, 42, len - 20, 10, 2.2);
      g.fillStyle = KD.kasavu; g.fillRect(-50, len - 18, 100, 13); meander(g, -46, len - 9, 46, 3.4, 1);
      for (let k = -2; k <= 2; k++) cutLine(g, 1.4, q => { q.moveTo(k * 8, 2); q.lineTo(k * 15, len - 20); });
    });
    ink(g, 1.8, s);
  }, { seed: 35 });
}
// sitting on the heels, knees forward, the mundu over the folded legs (waist at 0,0; ground at y = 74)
function kneel(col) {
  return piece([-60, -12, 96, 82], g => {
    const s = q => smooth(q, [[-24, -8], [24, -8], [52, 10], [78, 34], [86, 60], [80, 74], [20, 75], [-38, 74], [-46, 56], [-36, 24]]);
    fill(g, col, s);
    within(g, s, () => {
      g.fillStyle = KD.kasavu; g.fillRect(-60, 62, 160, 9); meander(g, -56, 69, 92, 3, .9);
      for (let k = 0; k < 4; k++) cutLine(g, 1.3, q => { q.moveTo(-12 + k * 14, 4 + k * 2); q.quadraticCurveTo(20 + k * 12, 26 + k * 4, 50 + k * 8, 50 + k * 2); });
      cutLine(g, 1.6, q => { q.moveTo(58, 20); q.quadraticCurveTo(74, 40, 72, 60); });
      g.fillStyle = DYE.ink; g.globalAlpha = .55; g.fillRect(-28, -8, 56, 5); g.globalAlpha = 1;
    });
    ink(g, 1.8, s);
    const foot = q => smooth(q, [[-36, 62], [-50, 64], [-58, 72], [-40, 76], [-30, 74]]);   // soles peeking out behind
    fill(g, KD.skin, foot); ink(g, 1.3, foot);
  }, { seed: 37 });
}

// ———————————————————— props ————————————————————
export function ilaneer() {      // tender coconut, top cut, with a straw
  return piece([-34, -70, 34, 34], g => {
    const s = q => smooth(q, [[-22, -24], [-8, -34], [10, -34], [24, -22], [27, 2], [16, 24], [0, 30], [-16, 24], [-26, 2]]);
    fill(g, KD.leaf2, s);
    within(g, s, () => { for (let k = -2; k <= 2; k++) cutLine(g, 1.2, q => { q.moveTo(k * 8, -26); q.quadraticCurveTo(k * 11, 0, k * 6, 24); }); });
    ink(g, 1.6, s);
    const cap = q => smooth(q, [[-10, -32], [0, -40], [12, -33], [4, -28]]); fill(g, KD.mundu2, cap); ink(g, 1.2, cap);
    ink(g, 3, q => { q.moveTo(2, -34); q.lineTo(14, -66); }, '#3a2414');
  }, { seed: 41 });
}
export function drop() { return piece([-6, -10, 6, 8], g => { const s = q => smooth(q, [[0, -9], [4, -1], [4.5, 3], [0, 6.5], [-4.5, 3], [-4, -1]]); fill(g, KD.water, s); ink(g, .8, s); }, { seed: 43 }); }
export function stick() { return piece([-20, -8, 10, 200], g => { ink(g, 7, q => { q.moveTo(0, 0); q.quadraticCurveTo(3, 90, 0, 196); }, '#2e180a'); ink(g, 6, q => { q.moveTo(0, 2); q.quadraticCurveTo(-14, -6, -16, 10); }, '#2e180a'); cutLine(g, 1.2, q => { q.moveTo(0, 30); q.lineTo(0.5, 170); }); }, { seed: 47 }); }

// ———————————————————— cast ————————————————————
function person(o) {
  const P = {
    head: headPiece(o.head), torso: torso(o.torso), ua: upperArm(o.sleeve, o.sleeveOpt), uaB: upperArm(o.sleeveB || o.sleeve, o.sleeveOpt),
    fa: foreArm(o.arm || {}), faB: foreArm(o.arm || {}), lower: o.lower, leg: o.leg || null
  };
  return { P, J: { ...J0, ...(o.J || {}) }, UA, FA, HAND, back: o.back, kneelH: o.kneelH || 0, legLen: o.legLen || 0 };
}
let CAST = null;
export function buildCast() {
  if (CAST) return CAST;
  const grandma = person({
    head: { k: 1.18, hair: KD.grey, bun: true, earring: true, wrinkles: true, smile: true, browCol: '#5a4a3c', seed: 5,
      hairIn: [[11, -64], [6, -60], [1, -52], [-2, -40], [-6, -24], [-11, -9]] },
    torso: { kind: 'blouse', col: KD.mundu2, seed: 22 }, sleeve: KD.mundu2, sleeveOpt: { sleeve: 22 }, arm: { bangles: 2 },
    lower: kneel(KD.mundu), kneelH: 74
  });
  const boy = person({
    head: { k: 1.3, fringe: true, seed: 6, hairIn: [[11, -64], [8, -60], [2, -52], [-3, -40], [-6, -24], [-11, -9]] },
    torso: { kind: 'shirt', col: KD.shirtG, col2: KD.leaf, seed: 23 }, sleeve: KD.shirtG, sleeveOpt: { sleeve: 24 },
    lower: shorts(KD.red), leg: leg(118), legLen: 118, J: { hipF: [8, 12], hipB: [-6, 12] }
  });
  const man = person({
    head: { k: 1.08, tache: true, seed: 7 },
    torso: { kind: 'shirt', col: KD.shirtO, col2: KD.gold, seed: 24 }, sleeve: KD.shirtO, sleeveOpt: { sleeve: 38 }, arm: { watch: true },
    lower: muduLong(150, KD.mundu), leg: leg(162, { feetOnly: true }), legLen: 162
  });
  const oldStand = person({
    head: { k: 1.12, hair: KD.grey, tache: true, tacheCol: KD.grey, glasses: true, wrinkles: true, smile: true, browCol: '#5a4a3c', seed: 8,
      hairIn: [[2, -68], [-1, -60], [-3, -48], [-4, -36], [-6, -24], [-11, -9]], hairOut: [[-11, -9], [-22, -16], [-29, -34], [-28, -52], [-20, -66], [-8, -72], [0, -70], [3, -69]] },
    torso: { kind: 'kurta', col: KD.mundu2, seed: 25 }, sleeve: KD.mundu2, sleeveOpt: { sleeve: 40 }, arm: { watch: true },
    lower: muduLong(150, KD.mundu), leg: leg(162, { feetOnly: true }), legLen: 162
  });
  const oldKneel = { ...oldStand, P: { ...oldStand.P, lower: kneel(KD.mundu), leg: null }, kneelH: 74, legLen: 0 };
  // Minnu: pigtails with red ribbons swing behind the head (pendulums)
  const tail = piece([-10, -4, 10, 46], g => {
    const s = q => smooth(q, [[-5, 0], [5, 0], [7, 18], [4, 40], [-3, 42], [-6, 20]]); fill(g, DYE.ink, s); within(g, s, () => { for (let k = 0; k < 3; k++) cutLine(g, .7, q => { q.moveTo(-3 + k * 3, 4); q.lineTo(-2 + k * 2.4, 38); }); }); ink(g, 1, s);
    const bow = q => { q.moveTo(0, 8); q.lineTo(-10, 2); q.lineTo(-10, 14); q.closePath(); q.moveTo(0, 8); q.lineTo(10, 2); q.lineTo(10, 14); q.closePath(); };
    fill(g, KD.red, bow, 'nonzero'); ink(g, 1, bow);
  }, { seed: 45 });
  const girl = person({
    head: { k: 1.34, fringe: true, jasmine: true, seed: 9, hairIn: [[11, -64], [8, -60], [2, -52], [-3, -40], [-6, -24], [-11, -9]] },
    torso: { kind: 'girl', col: KD.blouse, seed: 26 }, sleeve: KD.blouse, sleeveOpt: { sleeve: 20, puff: true }, arm: { bangles: 1 },
    lower: pavada(104), leg: leg(114, { anklet: true }), legLen: 114, J: { hipF: [8, 6], hipB: [-6, 6] },
    back: (p, Mhead) => { const sw = p.swing || 0; const at = (x, y, a) => mulM(Mhead, x, y, a); return [[tail, at(-30 * 1.34, -40 * 1.34, .5 + sw)], [tail, at(-24 * 1.34, -56 * 1.34, .9 + sw * 1.3)]]; }
  });
  CAST = { grandma, boy, man, oldStand, oldKneel, girl, ilaneer: ilaneer(), drop: drop(), stick: stick() };
  return CAST;
}
function mulM(M, x, y, a) { const c = Math.cos(a), s = Math.sin(a); const L = [c, s, -s, c, x, y]; return [M[0] * L[0] + M[2] * L[1], M[1] * L[0] + M[3] * L[1], M[0] * L[2] + M[2] * L[3], M[1] * L[2] + M[3] * L[3], M[0] * L[4] + M[2] * L[5] + M[4], M[1] * L[4] + M[3] * L[5] + M[5]]; }
