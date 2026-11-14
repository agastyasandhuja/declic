import {box} from './ModelKit';
const clamp = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => {x = clamp(x); return x*x*(3-2*x);};
const pulse = (u: number, start: number, length: number) => Math.sin(Math.PI*clamp((u-start)/length));

// Opt-in face layer: other ModelKit consumers retain their existing appearance.
export function addExpressionRig(actor: any) {
  const brows = [-.17, .17].map(x => box(actor.head, x, .135, .38, .19, .035, .025, '#554033'));
  const corners = [-.105, .105].map(x => box(actor.head, x, -.25, .365, .035, .055, .025, '#7e4035'));
  return {brows, corners};
}

// Every field is assigned from time, avoiding stale poses after a cut or seeking.
export function poseExpression(actor: any, rig: ReturnType<typeof addExpressionRig>, scene: string,
  u: number, time: number, index: number, lift: number) {
  const troubled = ['hook', 'empty', 'commons', 'cost'].includes(scene);
  const pleased = ['access', 'extra', 'restore'].includes(scene);
  const notice = scene === 'subtract' && index === 1 ? pulse(u, .45, .55) : 0;
  const surprise = (scene === 'empty' || scene === 'hook') ? pulse(u, .15+index*.045, .62) : 0;
  const worry = troubled ? .65 + surprise*.35 : scene === 'deplete' ? smooth((u-.5-index*.025)/.4) : 0;
  const smile = pleased ? .45 + lift*.45 : 0;
  const blink = ((time+index*.73)%3.7) < .10;
  actor.eyes.forEach((lid: any) => {lid.visible = blink;});
  // Geometry scales are absolute dimensions: the original mouth is 0.23 × 0.045.
  actor.mouth.scale.set(.23-surprise*.08, .045+surprise*.095, .025);
  actor.mouth.position.y = -.25;
  rig.brows.forEach((brow: any, i: number) => {
    brow.position.y = .135 + surprise*.06 + notice*.035;
    brow.rotation.z = (i ? -1 : 1)*(worry*.22-smile*.08);
  });
  rig.corners.forEach((corner: any, i: number) => {
    corner.visible = surprise < .4;
    corner.position.y = -.25 + smile*.035 - worry*.022;
    corner.rotation.z = (i ? -1 : 1)*(smile*.35-worry*.25);
  });
  // Reactions follow the catch or empty hook; the body stays oriented to its task.
  actor.head.rotation.x += surprise*.10 - lift*.06;
  actor.head.rotation.z += (index%2 ? -1 : 1)*(surprise*.06+notice*.08);
  return {notice, surprise, worry};
}
