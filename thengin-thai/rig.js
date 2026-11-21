// 2D affine helpers + a generic jointed shadow-puppet rig (forward kinematics for head/legs, two-bone IK for arms).
// Matrices are canvas setTransform order [a,b,c,d,e,f]: x' = a·x + c·y + e, y' = b·x + d·y + f. Rotation positive = clockwise (y down).
import { drawPiece, rivet } from './carve.js';

export const mul = (A, B) => [A[0] * B[0] + A[2] * B[1], A[1] * B[0] + A[3] * B[1], A[0] * B[2] + A[2] * B[3], A[1] * B[2] + A[3] * B[3], A[0] * B[4] + A[2] * B[5] + A[4], A[1] * B[4] + A[3] * B[5] + A[5]];
export const T = (x, y) => [1, 0, 0, 1, x, y];
export const R = a => { const c = Math.cos(a), s = Math.sin(a); return [c, s, -s, c, 0, 0]; };
export const S = (x, y = x) => [x, 0, 0, y, 0, 0];
export const ap = (M, x, y) => [M[0] * x + M[2] * y + M[4], M[1] * x + M[3] * y + M[5]];
export const inv = M => { const d = M[0] * M[3] - M[1] * M[2]; return [M[3] / d, -M[1] / d, -M[2] / d, M[0] / d, (M[2] * M[5] - M[3] * M[4]) / d, (M[1] * M[4] - M[0] * M[5]) / d]; };
export const set = (g, M) => g.setTransform(M[0], M[1], M[2], M[3], M[4], M[5]);

// Two-bone IK in the figure's local space. Bones hang along +y at rotation 0, so a world direction φ is rotation φ − π/2.
// bend = +1 puts the elbow/knee "behind" (toward −x locally), −1 in front. Returns [a1 (upper, absolute), a2 (lower, relative to upper)].
export function ik(sh, p, L1, L2, bend = 1) {
  const dx = p[0] - sh[0], dy = p[1] - sh[1], d = Math.max(1e-3, Math.min(Math.hypot(dx, dy), L1 + L2 - .5));
  const th = Math.atan2(dy, dx), al = Math.acos(Math.max(-1, Math.min(1, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))));
  const u = th + bend * al, e = [sh[0] + Math.cos(u) * L1, sh[1] + Math.sin(u) * L1];
  const f = Math.atan2(p[1] - e[1], p[0] - e[0]);
  return [u - Math.PI / 2, f - u];
}

// fig = { P: pieces, J: joints, UA, FA, order? }, pose = { x, y, dir, sc, rot, head, aF, aB, lF, lB, prop, propRot, propAt }
// arm spec: [a1, a2] angles, or { to: [wx, wy], bend } for a world-space hand target.
// opt: { press: 0..1 (1 = flat on the cloth), lift: 0..1 (0 = on the cloth), alpha, rivets, k (camera scale) }
export function drawFigure(g, Cam, fig, pose, opt = {}) {
  const p = { rot: 0, head: 0, lF: 0, lB: 0, dir: 1, sc: 1, ...pose };
  const press = opt.press ?? 1, lift = opt.lift ?? 0;
  if (lift >= 1 || press <= 0) return null;
  const k = Math.hypot(Cam[0], Cam[1]);
  // Off the screen = big and blurry: scale about the figure's own waist
  const grow = (1 + (1 - press) * 1.6) * (1 + lift * .9);
  const blur = ((1 - press) * 34 + lift * 30) * k;
  const alpha = (.35 + .65 * press) * (1 - lift * lift * lift) * (opt.alpha ?? 1);
  const W0 = mul(T(p.x, p.y), mul(S(p.dir * p.sc, p.sc), R(p.rot)));
  const C2 = mul(Cam, mul(T(p.x, p.y), mul(S(grow), T(-p.x, -p.y))));
  const W = mul(C2, W0), J = fig.J, Pc = fig.P;
  const Wi = inv(W0);
  const arm = (side, spec) => {
    const sh = J[side === 'F' ? 'shF' : 'shB'];
    let a1, a2;
    if (spec && spec.to) { const lp = ap(Wi, spec.to[0], spec.to[1]);[a1, a2] = ik(sh, lp, fig.UA, fig.FA + (fig.HAND || 0), spec.bend ?? 1); }
    else[a1, a2] = spec || [0, 0];
    const Mu = mul(W, mul(T(sh[0], sh[1]), R(a1)));
    const Mf = mul(Mu, mul(T(0, fig.UA), R(a2 + (spec && spec.wrist || 0) * 0)));
    const Mh = mul(Mf, mul(T(0, fig.FA), R(spec && spec.hand || 0)));
    return { Mu, Mf, Mh };
  };
  const B = arm('B', p.aB), F = arm('F', p.aF);
  const Mhead = mul(W, mul(T(J.neck[0], J.neck[1]), R(p.head)));
  const MlB = J.hipB ? mul(W, mul(T(J.hipB[0], J.hipB[1]), R(p.lB))) : null;
  const MlF = J.hipF ? mul(W, mul(T(J.hipF[0], J.hipF[1]), R(p.lF))) : null;
  g.save(); g.globalCompositeOperation = 'multiply'; g.globalAlpha = Math.max(0, alpha);
  if (blur > .3) g.filter = `blur(${blur.toFixed(1)}px)`;
  const dp = (M, pc) => { if (!pc) return; set(g, M); drawPiece(g, pc); };
  if (fig.back) for (const [pc, Mf] of fig.back(p, Mhead, W)) dp(Mf, pc);      // loose parts behind (pigtails…)
  dp(B.Mu, Pc.uaB || Pc.ua); dp(B.Mf, Pc.faB || Pc.fa);
  if (p.propB) dp(mul(B.Mh, mul(T(...(p.propB.at || [0, 0])), R(p.propB.rot || 0))), p.propB.pc);
  if (MlB && Pc.leg) dp(MlB, Pc.legB || Pc.leg);
  if (MlF && Pc.leg) dp(MlF, Pc.leg);
  dp(W, Pc.lower); dp(W, Pc.torso); dp(Mhead, Pc.head);
  dp(F.Mu, Pc.ua); dp(F.Mf, Pc.fa);
  if (p.prop && p.prop.vertical) { const q = ap(F.Mh, ...(p.prop.at || [0, 0])), kk = Math.hypot(W[0], W[1]); dp([kk, 0, 0, kk, q[0], q[1]], p.prop.pc); }
  else if (p.prop) dp(mul(F.Mh, mul(T(...(p.prop.at || [0, 0])), R(p.prop.rot || 0))), p.prop.pc);
  g.restore();
  // Thread rivets at every joint (only when on the cloth)
  if (opt.rivets !== false && press > .9 && lift < .1) {
    g.save(); g.globalAlpha = alpha; g.setTransform(1, 0, 0, 1, 0, 0);
    const r = 3.2 * k * p.sc, pts = [ap(W, ...J.neck), ap(W, ...J.shF), ap(B.Mu, 0, fig.UA), ap(F.Mu, 0, fig.UA), ap(B.Mf, 0, fig.FA), ap(F.Mf, 0, fig.FA)];
    if (MlF) pts.push(ap(W, ...J.hipF)); if (MlB) pts.push(ap(W, ...J.hipB));
    for (const q of pts) rivet(g, q[0], q[1], r);
    g.restore();
  }
  return { W, Mhead, rods: [ap(W, ...J.rod), ap(F.Mh, 0, 6), ap(B.Mh, 0, 6)], hand: ap(mul(Cam, inv(Cam)), 0, 0), F, B, blur, alpha };
}

// Thin control rods, soft and grey, just off the cloth
export function drawRods(g, pts, ends, blur = 2.5, alpha = .6) {
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'multiply'; g.filter = `blur(${blur}px)`; g.globalAlpha = alpha;
  pts.forEach((p, i) => {
    const e = ends[i]; g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(e[0], e[1]); g.strokeStyle = '#2a1a10'; g.lineWidth = i === 0 ? 4 : 2.6; g.stroke();
    g.beginPath(); g.arc(p[0], p[1], i === 0 ? 3.8 : 2.8, 0, Math.PI * 2); g.fillStyle = '#2a1a10'; g.fill();
  });
  g.restore();
}
