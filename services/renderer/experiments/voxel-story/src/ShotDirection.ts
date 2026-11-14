// Original, frame-addressable shot direction inspired by claude-animated-shorts.
// Camera plans are authored code, never executable model output. No new packages.
export const DIRECTION_VERSION = 'voxel-cinematic-v3';
type Vec3 = [number, number, number];
type Word = {text: string; start: number; end: number};
type Beat = {scene: string; start: number; end: number; camera: [Vec3, Vec3]; target: Vec3};
type View = {position: Vec3; target: Vec3; fov: number; roll: number};
type Key = View & {at: number; cut?: boolean};
const clamp = (x: number) => Math.max(0, Math.min(1, x));
const glide = (x: number) => {x = clamp(x); return x*x*x*(x*(x*6-15)+10);};
const mix = (a: number, b: number, p: number) => a+(b-a)*p;
const vector = (a: Vec3, b: Vec3, p: number): Vec3 => a.map((v, i) => mix(v, b[i], p)) as Vec3;
const view = (at: number, position: Vec3, target: Vec3, fov = 46, cut = false, roll = 0): Key =>
  ({at, position, target, fov, cut, roll});

// Only words inside this beat can move a cue. Missing alignment uses the authored
// fraction; a late/early word cannot erase the action or reorder the camera keys.
export function wordCue(beat: Beat, words: Word[], token: string, fallback: number, min = .2, max = .8) {
  const word = words.find(w => w.start >= beat.start && w.start < beat.end &&
    w.text.toLowerCase().replace(/[^a-z]/g, '') === token);
  const fraction = word ? (word.start-beat.start)/Math.max(.01, beat.end-beat.start) : fallback;
  return Math.max(min, Math.min(max, fraction));
}

// The lake keeps its existing catch/blocking timeline. Insets observe the actual
// action: do not retime transfers just to match a camera cut or a spoken word.
export function lakeShotPlan(beat: Beat, words: Word[]): Key[] {
  const cue = (word: string, fallback: number, min = .2, max = .8) => wordCue(beat, words, word, fallback, min, max);
  switch (beat.scene) {
    case 'hook': return [
      view(0, [2.9, 2.8, 1.2], [0, 1.75, 3.8], 43),
      view(cue('dinner', .65), [2.5, 2.7, 1.5], [0, 1.9, 3.8], 40),
      view(1, [2.4, 2.7, 1.6], [0, 1.9, 3.8], 40),
    ];
    case 'access': return [
      view(0, [10, 10, 12], [0, .4, 1.2], 48),
      // Fish lifts at ~.44 and deposits at ~.73 of this beat.
      view(.40, [3.8, 3.6, .8], [.3, 1.1, 3.3], 48, true),
      view(.78, [3.4, 3.3, 1.0], [.5, 1.05, 3.6], 46),
      view(1, [3.3, 3.3, 1.1], [.5, 1.05, 3.6], 46),
    ];
    case 'subtract': return [
      view(0, [4.2, 3.6, .6], [.4, 1.2, 3.6], 48),
      view(.72, [5.3, 3.5, .4], [1.6, 1.5, 4.0], 49),
      view(1, [5.2, 3.4, .5], [1.6, 1.5, 4.0], 48),
    ];
    case 'extra': return [
      view(0, [3.8, 3.5, .7], [.35, 1.35, 3.7], 48),
      view(.50, [3.3, 3.3, 1.0], [.4, 1.25, 3.7], 47),
      view(1, [3.2, 3.2, 1.1], [.4, 1.25, 3.7], 47),
    ];
    case 'rush': return [
      view(0, [10, 8, 9], [0, 1, 1.5], 52),
      view(cue('brilliant', .58), [9, 7.5, 8], [0, 1, 1.5], 52),
      view(1, [8.5, 7, 7.5], [0, 1, 1.5], 52),
    ];
    case 'deplete': return [
      view(0, [7.5, 10, 9], [0, 0, 0], 52),
      view(.52, [5.5, 12, 6], [0, -.3, 0], 49),
      view(1, [4.5, 13, 5], [0, -.3, 0], 47),
    ];
    case 'empty': return [
      view(0, [3.4, 3.2, 1], [0, 1.65, 3.8], 45),
      view(cue('nothing', .64), [2.8, 2.9, 1.4], [0, 1.8, 3.8], 42),
      view(1, [2.7, 2.9, 1.5], [0, 1.8, 3.8], 42),
    ];
    case 'commons': return [
      view(0, [4.8, 4.2, .4], [.6, 1, 3.7], 48),
      view(cue('shared', .70), [9, 10, 10], [0, .1, .5], 51, true),
      view(1, [8.6, 9.7, 9.6], [0, .1, .5], 51),
    ];
    case 'cost': return [
      view(0, [-6, 5, .6], [-.3, 1.1, 3.4], 49),
      view(cue('others', .72), [-5.3, 4.5, .8], [-.5, 1.2, 3.5], 48),
      view(1, [-5.2, 4.5, .9], [-.5, 1.2, 3.5], 48),
    ];
    case 'rules': return [
      view(0, [6.4, 4.4, .9], [1.9, 1.35, 4.5], 48),
      view(cue('reproduce', .77, .65, .85), [8, 9, 10], [0, .2, 1.4], 50, true),
      view(1, [8.4, 9.6, 10.4], [0, .2, 1.4], 50),
    ];
    case 'restore': return [
      view(0, [3.8, 4.1, .8], [0, 1.0, 3.3], 48),
      // Hold on the release until the existing hand-to-water action finishes.
      view(.68, [4.1, 4.7, .9], [0, .5, 2.6], 48),
      view(1, [8, 10, 8], [0, .2, 1.5], 50),
    ];
    default: return [view(0, beat.camera[0], beat.target), view(1, beat.camera[1], beat.target)];
  }
}

// Pure sampling supports Remotion's out-of-order/concurrent frame rendering.
// A cut switches exactly at its key; other keys use a bounded smootherstep glide.
export function sampleShot(keys: Key[], progress: number): View {
  const p = clamp(progress);
  let a = keys[0];
  for (let i = 1; i < keys.length; i++) {
    const b = keys[i];
    if (p < b.at) {
      if (b.cut) return {...a};
      const q = glide((p-a.at)/Math.max(.001, b.at-a.at));
      return {position: vector(a.position, b.position, q), target: vector(a.target, b.target, q),
        fov: mix(a.fov, b.fov, q), roll: mix(a.roll, b.roll, q)};
    }
    a = b;
  }
  return {...a};
}

// Captions stay in one safe location per beat so reading doesn't chase the camera.
export const lakeCaptionTop = (scene: string) =>
  ['hook', 'access', 'subtract', 'extra', 'empty', 'cost', 'rules', 'restore'].includes(scene) ? 920 : 900;
