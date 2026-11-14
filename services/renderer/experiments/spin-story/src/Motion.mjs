export const clamp=x=>Math.max(0,Math.min(1,x));
export const smooth=x=>{const u=clamp(x);return u*u*u*(u*(u*6-15)+10)};
export const mix=(a,b,u)=>a+(b-a)*u;
export const WIDE=.8;
// Illustrative inertia model: fixed body/chair + two symmetric point masses.
export const inertia=r=>1+2*(r*r+.01);
export const TUCK=Math.sqrt((inertia(WIDE)/2-1)/2-.01);
export function elbow(side,r){
 const a=[side*.22,0],b=[side*r,.1],dx=b[0]-a[0],dy=b[1]-a[1],d=Math.hypot(dx,dy);
 const h=Math.sqrt(Math.max(0,.42*.42-d*d/4));
 // Both limbs bend forward continuously; no IK branch switching.
 return [(a[0]+b[0])/2+side*dy/d*h,(a[1]+b[1])/2-side*dx/d*h];
}
export function makeTrack(lesson){
 const beats=Object.fromEntries(lesson.segments.map(s=>[s.scene,s]));
 const phase=(name,t,a=.15,b=.8)=>smooth((t-beats[name].start-(beats[name].end-beats[name].start)*a)/((beats[name].end-beats[name].start)*(b-a)));
 const duration=lesson.frames/30,dt=1/240,L0=inertia(WIDE)*1.35;
 function state(t){
  let r=WIDE,L=L0,feet=0;
  const b=lesson.segments.find(s=>t>=s.start&&t<s.end)||lesson.segments.at(-1),name=b.scene;
  if(name==='hook'){
   L=L0*smooth((t-.35)/.9);r=mix(WIDE,TUCK,smooth((t-2.2)/1.5));feet=1-smooth((t-1.05)/.4);
  }else if(name==='above'||name==='isolated')r=WIDE;
  else if(name==='inward')r=mix(WIDE,TUCK,phase('inward',t));
  else if(name==='faster')r=TUCK;
  else if(name==='outward')r=mix(TUCK,WIDE,phase('outward',t));
  else if(name==='double')r=mix(WIDE,TUCK,phase('double',t));
  else r=TUCK;
  if(name==='brake'){const p=phase('brake',t,.24,.9);feet=phase('brake',t,.05,.24);L=L0*(1-p)}
  if(name==='outro'){feet=1;L=0;r=mix(TUCK,WIDE,phase('outro',t))}
  const I=inertia(r),omega=L/I;
  return {r,I,L,omega,energy:.5*I*omega*omega,feet,scene:name};
 }
 const angles=[0];
 for(let n=1;n<=Math.ceil(duration/dt)+1;n++){
  const ta=(n-1)*dt,tb=n*dt;
  // Deliberate rewind edit into the overhead replay; continuity elsewhere.
  const reset=ta<beats.above.start&&tb>=beats.above.start;
  angles[n]=reset?0:angles[n-1]+(state(ta).omega+state(tb).omega)*dt/2;
 }
 return t=>{const n=Math.min(angles.length-2,Math.max(0,Math.floor(t/dt))),q=clamp(t/dt-n);return {...state(t),angle:mix(angles[n],angles[n+1],q)}};
}
