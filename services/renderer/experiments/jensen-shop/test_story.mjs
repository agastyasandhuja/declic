import test from 'node:test';
import assert from 'node:assert/strict';
import {armSolution,state} from './src/Story.mjs';
const lesson={segments:Array.from({length:8},(_,i)=>({start:i*5,end:(i+1)*5}))};
const distance=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));
test('one GPU changes custody exactly once per transfer; cash remains after cost entry',()=>{
 const owners=[];for(let t=0;t<40;t+=.01){const s=state(lesson,t);if(owners.at(-1)!==s.gpuOwner)owners.push(s.gpuOwner);if(t>=10.9)assert.equal(s.cashOwner,'drawer')}
 assert.deepEqual(owners,['shelf','jensen','customer']);assert.equal(state(lesson,35).secondEntry,true);assert.equal(state(lesson,35).ledgerAmount,40);
});
test('two bone grip preserves arm lengths and reaches valid targets',()=>{
 for(const target of [[.5,1.3,.55],[-.6,1.6,-.2],[.3,2.4,.2]]){
  const shoulder=[.58,1.9,0],p=armSolution(shoulder,target,1);
  assert.ok(Math.abs(distance(shoulder,p.elbow)-.52)<1e-9);assert.ok(Math.abs(distance(p.elbow,p.hand)-.5)<1e-9);
  if(distance(shoulder,target)<=1.019)assert.ok(distance(p.hand,target)<1e-9);
 }
});
test('actors settle on the floor and customer exits in front of the counter',()=>{
 for(let t=0;t<40;t+=.03){const s=state(lesson,t);for(const person of [s.jensen,s.customer,s.bookkeeper])assert.equal(person[1],0);assert.ok(s.customer[2]>=.75-1e-9)}
});
