// Timeline: the single source of truth for picture, voice, music, foley and subtitles. 96 bpm where there is pulse (beat 0.625 s).
export const BEAT = .625;
export const DUR = 52.0;
export const T = {
  lamp0: .35, holeGlow: .45, lamp1: 1.3, lamp2: 1.7, curtainOff: 2.0, press: 2.6,
  run0: 4.9, run1: 6.05, hop: 6.05, freeze: 6.3,
  pushClose: 15.95, tap: 16.4, tilt0: 18.3, tilt1: 21.5, walk0: 19.0, walk1: 20.8, back: 21.7,
  headPat: 22.9, headPat1: 24.9, pour0: 25.3, pour1: 26.6,
  scrape: 26.8, swaps: [28.4, 30.0, 31.6, 33.2, 34.8], liftGrandma: 30.0, bigGong: 34.8,
  oldRekneel: 35.35, sprout2: 35.6, girl0: 35.9, girl1: 36.45, girlStep0: 38.95, girlStep1: 39.7, oldPat: 40.2,
  pull0: 41.3, pull1: 44.6, title0: 45.5, title1: 46.2, carry0: 49.3, carry1: 51.5, stop: 51.6
};
// Lines: start times; durations come from voice/out/dur.json. who: dialogue (100 %) or narrator (75 %).
export const LINES = [
  { id: 'n1', t: 2.9, who: 'narrator' }, { id: 'a1', t: 6.45, who: 'appu' }, { id: 'a2', t: 8.9, who: 'appu' },
  { id: 'g1', t: 11.3, who: 'ammumma' }, { id: 'a3', t: 13.6, who: 'appu' }, { id: 'g2', t: 16.9, who: 'ammumma' },
  { id: 'g3', t: 22.3, who: 'ammumma' }, { id: 'n2', t: 27.3, who: 'narrator' }, { id: 'm1', t: 36.6, who: 'minnu' },
  { id: 'p1', t: 39.35, who: 'oldappu' }, { id: 'n3', t: 42.3, who: 'narrator' }
];
export const SHOTS = [[0, 2.6, 'open'], [2.6, 6.4, 'press'], [6.4, 15.9, 'two'], [15.9, 21.7, 'answer'], [21.7, 26.8, 'close'],
  [26.8, 35.6, 'years'], [35.6, 41.3, 'echo'], [41.3, 52.01, 'end']];
export const shotAt = t => SHOTS.find(s => t >= s[0] && t < s[1]) || SHOTS[SHOTS.length - 1];
// Fluency edits: pauses trimmed out of a line (seconds in the TTS file); the subtitle of a line can be split at a time (edited timeline)
export const CUTS = { g2: [[2.45, 3.1]] };
export const SPLIT = { g2: 2.45 };
export const editedDur = (id, d) => d - (CUTS[id] || []).reduce((a, [x, y]) => a + (y - x), 0);
