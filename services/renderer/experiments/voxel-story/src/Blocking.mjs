// Codex-authored reusable blocking: +Z is a character's face, not the camera.
export const clamp=x=>Math.max(0,Math.min(1,x));
export const ease=x=>{x=clamp(x);return x*x*(3-2*x)};
export const mix=(a,b,t)=>a+(b-a)*t;
export const facing=(origin,target)=>Math.atan2(target[0]-origin[0],target[1]-origin[1]);
export const turn=(a,b,t)=>a+Math.atan2(Math.sin(b-a),Math.cos(b-a))*ease(t);
export const spots=[[0,4.2],[3.6,4.2],[-3.6,4.2],[5.6,1.8],[-5.6,1.2],[3.4,-4.2],[-3.7,-4.2]];
export const waterTargets=spots.map(([x,z])=>[x*.62,z*.45]);
const paths=[[[0,4.2],[0,4.2],[0,4.2]],[[8,7],[6,5],[3.6,4.2]],[[-8,7],[-6,5],[-3.6,4.2]],[[8,-7],[5.8,-4.5],[5.6,1.8]],[[-8,-7],[-5.8,-4.5],[-5.6,1.2]],[[3.4,-8],[3.4,-6],[3.4,-4.2]],[[-3.7,-8],[-3.7,-6],[-3.7,-4.2]]];
export function walkToSpot(i,u){
 const q=clamp((u-i*.035)/.72),p=paths[i],leg=q<.5?0:1,t=q<.5?q*2:(q-.5)*2;
 const position=[mix(p[leg][0],p[leg+1][0],t),mix(p[leg][1],p[leg+1][1],t)];
 const walkingYaw=facing(p[leg],p[leg+1]);
 return {position,yaw:turn(walkingYaw,facing(spots[i],waterTargets[i]),(q-.86)/.14),moving:q>0&&q<1};
}
export const eventsFor=scene=>{
 if(scene==='access')return [{actor:0,fish:23,start:.08,end:.93}];
 if(scene==='subtract')return [{actor:0,fish:22,start:.05,end:.92}];
 if(scene==='extra')return [0,1].map(i=>({actor:0,fish:21-i,start:i*.46,end:i*.46+.43}));
 if(scene==='deplete')return Array.from({length:18},(_,i)=>({actor:i%7,fish:19-i,start:Math.floor(i/7)*.29+i%7*.023,end:Math.floor(i/7)*.29+i%7*.023+.32}));
 return [];
};
export function posePhase(q){
 // Anticipate → cast → wait → reel/lift → turn/deposit → settle.
 return {wind:Math.sin(Math.PI*clamp(q/.18)),cast:ease((q-.13)/.2),
  lift:ease((q-.42)/.29),deposit:ease((q-.76)/.17),
  turnToCrate:ease((q-.68)/.13)*(1-ease((q-.93)/.07))};
}
