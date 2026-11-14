import test from 'node:test';
import assert from 'node:assert/strict';
import {states,tally,totals} from '../experiments/election-story/src/ElectionMath.mjs';
import {makeTrack,elbow,inertia,WIDE,TUCK} from '../experiments/spin-story/src/Motion.mjs';
const scenes=['hook','above','isolated','inward','faster','outward','double','energy','brake','outro'];
const lesson={frames:1200,segments:scenes.map((scene,i)=>({scene,start:i*4,end:(i+1)*4}))};
const at=makeTrack(lesson);

test('winner-take-all transfers each electoral vote once despite a popular-vote reversal',()=>{
 assert.equal(totals.popular.orange+totals.popular.teal,300);
 assert.equal(totals.electoral.orange+totals.electoral.teal,states.reduce((n,s)=>n+s.electors,0));
 assert.ok(totals.popular.orange>totals.popular.teal);
 assert.ok(totals.electoral.orange<totals.electoral.teal);
 const changed=tally(states.map((s,i)=>i===1?{...s,teal:49,orange:51}:s));
 assert.equal(changed.electoral.orange,10);assert.equal(changed.electoral.teal,5);
 assert.throws(()=>tally([{teal:50,orange:50,electors:5}]));
});
test('spinning rig preserves connected limb lengths throughout the complete action',()=>{
 for(let t=0;t<40;t+=1/120){const m=at(t);for(const side of [-1,1]){
  const e=elbow(side,m.r);
  assert.ok(Math.abs(Math.hypot(e[0]-side*.22,e[1])-.42)<1e-10);
  assert.ok(Math.abs(Math.hypot(e[0]-side*m.r,e[1]-.1)-.42)<1e-10);
 }}
});
test('inward/outward motion changes spin and energy while conserving momentum',()=>{
 const wide=at(10),tucked=at(18),extended=at(23.8);
 assert.ok(Math.abs(tucked.omega/wide.omega-2)<1e-10);
 assert.ok(tucked.energy>wide.energy);assert.ok(extended.omega<tucked.omega);
 for(let t=4.01;t<32;t+=1/120)assert.ok(Math.abs(at(t).I*at(t).omega-inertia(WIDE)*1.35)<1e-10);
 assert.ok(Math.abs(inertia(WIDE)/inertia(TUCK)-2)<1e-10);
});
test('rotation stays continuous except the explicit rewind, then floor torque stops it',()=>{
 for(let t=.01;t<40;t+=1/240){if(Math.abs(t-4)<.02)continue;assert.ok(Math.abs(at(t).angle-at(t-1/240).angle)<.012)}
 assert.equal(at(32).feet,0);assert.equal(at(34).feet,1);
 assert.ok(at(34).L<at(32).L);assert.equal(at(39).omega,0);
 assert.equal(at(38).angle,at(39).angle);
});
