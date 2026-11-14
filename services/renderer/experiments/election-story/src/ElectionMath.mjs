// A toy demonstration, not a real map, allocation or election result.
export const states=Object.freeze([
 {id:'A',teal:51,orange:49,electors:5,x:-4,z:-1.8},
 {id:'B',teal:51,orange:49,electors:5,x:0,z:1},
 {id:'C',teal:2,orange:98,electors:5,x:4,z:-1.8},
]);
export function tally(rows){
 const result={popular:{teal:0,orange:0},electoral:{teal:0,orange:0}};
 for(const s of rows){
  if(![s.teal,s.orange,s.electors].every(v=>Number.isInteger(v)&&v>=0)||s.teal===s.orange)throw Error('Requires a non-tied, nonnegative example');
  result.popular.teal+=s.teal;result.popular.orange+=s.orange;
  result.electoral[s.teal>s.orange?'teal':'orange']+=s.electors;
 }
 return result;
}
export const totals=tally(states);
export const clamp=x=>Math.max(0,Math.min(1,x));
export const ease=x=>{const u=clamp(x);return u*u*u*(u*(u*6-15)+10)};
export const mix=(a,b,p)=>a+(b-a)*p;
export const yaw=(a,b)=>Math.atan2(b[0]-a[0],b[1]-a[1]);
