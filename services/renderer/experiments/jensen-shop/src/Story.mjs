// Pure, deterministic choreography; no elapsed browser time or random motion.
export const clamp=x=>Math.max(0,Math.min(1,x));
export const ease=x=>{const u=clamp(x);return u*u*(3-2*u)};
export const mix=(a,b,u)=>a.map((v,i)=>v+(b[i]-v)*ease(u));
export function beat(lesson,t){const i=Math.max(0,lesson.segments.findLastIndex(s=>s.start<=t));const s=lesson.segments[i];return {i,u:clamp((t-s.start)/(s.end-s.start))}}
export function state(lesson,t){
 const {i,u}=beat(lesson,t);const sold=i>2||(i===2&&u>=.70);
 return {i,u,sold,gpuOwner:i<2||(i===2&&u<.30)?'shelf':sold?'customer':'jensen',
  cashOwner:i<2||(i===2&&u<.18)?'customer':'drawer',
  firstEntry:i>=4,secondEntry:i>=6||(i===5&&u>.8),profit:i>=6,
  jensen:[i===2?-.30*(1-ease((u-.35)/.30)):i<2?-.30:0,0,-.65],
  customer:i<2?[0,0,1.8-(i===1?ease(u)*1.05:0)]:i===2&&u>.76?mix([0,0,.75],[3.2,0,1.8],(u-.76)/.24):i>2?[3.2,0,1.8]:[0,0,.75],
  bookkeeper:[1.25,0,-.65],
  gpuShelf:[-.9,1.55,-.65],handoff:[.25,1.6,0],
  ledgerAmount:i>=6?40:i>=5?60:100};
}
export function armSolution(shoulder,target,side=1){
 const sub=(a,b)=>a.map((x,i)=>x-b[i]),dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),norm=a=>Math.sqrt(dot(a,a));
 const raw=sub(target,shoulder),distance=Math.max(.08,Math.min(1.019,norm(raw))),direction=raw.map(x=>x/(norm(raw)||1));
 const hint=[side*.8,-.2,.8],projection=dot(hint,direction);let normal=hint.map((x,i)=>x-projection*direction[i]);normal=normal.map(x=>x/(norm(normal)||1));
 const along=(.52*.52-.5*.5+distance*distance)/(2*distance),height=Math.sqrt(Math.max(0,.52*.52-along*along));
 return {elbow:shoulder.map((x,i)=>x+direction[i]*along+normal[i]*height),hand:shoulder.map((x,i)=>x+direction[i]*distance)};
}
