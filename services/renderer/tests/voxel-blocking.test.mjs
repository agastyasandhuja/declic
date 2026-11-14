import test from 'node:test';
import assert from 'node:assert/strict';
import {facing,turn,spots,waterTargets,walkToSpot,eventsFor} from '../experiments/voxel-story/src/Blocking.mjs';

test('every bank position faces the lake, independent of camera position',()=>{
 for(let i=0;i<spots.length;i++){
  const [x,z]=spots[i],target=waterTargets[i],a=facing([x,z],target);
  const dx=target[0]-x,dz=target[1]-z;
  const dot=(Math.sin(a)*dx+Math.cos(a)*dz)/Math.hypot(dx,dz);
  assert.ok(dot>.999,`actor ${i} faces away from fishing target`);
 }
});
test('crowd approaches stay on dry banks and arrive without teleporting',()=>{
 for(let i=1;i<spots.length;i++){
  let previous=null;
  for(let step=0;step<=300;step++){
   const {position:[x,z]}=walkToSpot(i,step/300);
   assert.ok(Math.abs(x)>=5||Math.abs(z)>=3.5,`actor ${i} crossed water`);
   if(previous)assert.ok(Math.hypot(x-previous[0],z-previous[1])<.15,'discontinuous path');
   previous=[x,z];
  }
  assert.ok(Math.hypot(previous[0]-spots[i][0],previous[1]-spots[i][1])<1e-9);
 }
});
test('each harvested fish has one destination and an ordered transfer interval',()=>{
 const ids=new Set();
 for(const scene of ['access','subtract','extra','deplete']){
  for(const e of eventsFor(scene)){
   assert.ok(e.start>=0&&e.start<e.end&&e.end<=1);
   assert.ok(e.actor>=0&&e.actor<7);
   assert.ok(!ids.has(e.fish),'fish was caught twice');ids.add(e.fish);
  }
 }
 assert.equal(ids.size,22);assert.ok(!ids.has(0)&&!ids.has(1),'two fish remain');
});
test('turning takes the short path across the angle wrap',()=>{
 const a=179*Math.PI/180,b=-179*Math.PI/180;
 assert.ok(Math.abs(turn(a,b,.5)-a)<Math.PI/180+.001);
});
