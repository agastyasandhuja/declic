import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';

// Fixed procedural geometry: deterministic frames, no network or application credentials.
const rnd=(n:number)=>{const v=Math.sin(n*127.1+311.7)*43758.5453;return v-Math.floor(v)};
const stars=Array.from({length:1000},(_,i)=>({x:(rnd(i+1)-.5)*3400,y:(rnd(i+701)-.5)*4600,z:rnd(i+1401)*2600,r:.7+rnd(i+2101)*2.8}));
const galaxies=Array.from({length:900},(_,i)=>{
 const radius=Math.pow(rnd(i+2801),.65)*810,arm=i%4,angle=radius*.008+arm*Math.PI/2+(rnd(i+3501)-.5)*.7;
 return {x:Math.cos(angle)*radius,y:Math.sin(angle)*radius,z:(rnd(i+4201)-.5)*(80+radius*.16),r:1+rnd(i+4901)*3};
});
const nodes=Array.from({length:70},(_,i)=>({x:(rnd(i+5601)-.5)*2900,y:(rnd(i+6301)-.5)*3500,z:(rnd(i+7001)-.5)*2200}));
const edges=nodes.flatMap((n,i)=>nodes.map((m,j)=>({i,j,d:Math.hypot(n.x-m.x,n.y-m.y,n.z-m.z)})).filter(e=>e.j>i&&e.d<1050));
const wrap=(v:number,n:number)=>((v%n)+n)%n;
export const SpaceScene=({shot,images={}}:{shot:any,images:any})=>{
 const t=useCurrentFrame()/30,p=Math.max(0,Math.min(1,(t-shot.start)/(shot.end-shot.start)));
 const mode=shot.space_mode,orbit=shot.camera==='orbit';
 const theta=t*.025+(orbit?p*.28:0),tilt=.67+Math.sin(t*.04)*.14;
 const zoom=shot.camera==='pull'?1.8-p*1.1:shot.camera==='push'?.7+p*.9:1;
 const project=(x:number,y:number,z:number)=>{
  const rx=x*Math.cos(theta)-z*Math.sin(theta),rz=x*Math.sin(theta)+z*Math.cos(theta);
  const ry=y*Math.cos(tilt)-rz*Math.sin(tilt),depth=y*Math.sin(tilt)+rz*Math.cos(tilt)+2900;
  const travel=shot.camera==='push'?p*300:shot.camera==='pull'?-p*200:Math.sin(t*.08)*150;
  const k=1900/Math.max(500,depth-travel)*zoom;
  return {x:540+rx*k,y:870+ry*k,k};
 };
 const image=images[shot.asset_ids?.[0]];
 return <AbsoluteFill style={{background:'#02030b',overflow:'hidden'}}>
  <AbsoluteFill style={{background:`radial-gradient(ellipse at ${35+Math.sin(t*.1)*12}% 43%,#16316188,transparent 55%),radial-gradient(ellipse at 80% 65%,#64194f66,transparent 50%)`,transform:`scale(${1.1+p*.15})`}}/>
  {image&&<Img src={staticFile(image.file)} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',opacity:mode==='nebula'?.72:mode==='galaxy'?.38:.13,mixBlendMode:'screen',transform:`scale(${1.15+p*.25}) rotate(${t*.18}deg)`}}/>}
  <svg viewBox="0 0 1080 1920" style={{position:'absolute',inset:0,width:'100%',height:'100%'}}>
   <defs>
    <radialGradient id="galaxyGlow"><stop stopColor="#fff5dc" stopOpacity=".95"/><stop offset=".13" stopColor="#e3ceef" stopOpacity=".6"/><stop offset=".42" stopColor="#5b83c3" stopOpacity=".18"/><stop offset="1" stopColor="#3d528a" stopOpacity="0"/></radialGradient>
    <radialGradient id="sunGlow"><stop stopColor="#fff4d0"/><stop offset=".2" stopColor="#ffbd5e"/><stop offset=".5" stopColor="#ff7b21" stopOpacity=".17"/><stop offset="1" stopColor="#ff7b21" stopOpacity="0"/></radialGradient>
    <filter id="filamentGlow"><feGaussianBlur stdDeviation="5"/></filter>
   </defs>
   {stars.map((s,i)=>{
    const depth=wrap(s.z-t*(mode==='starfield'?180:55),2600)+300,k=1400/depth;
    const x=540+(s.x+Math.sin(t*.03)*150)*k,y=900+s.y*k;
    return <circle key={i} cx={x} cy={y} r={Math.min(4,s.r*k)} fill={i%7===0?'#b1caff':i%11===0?'#ffc9a9':'#eef4ff'} opacity={Math.min(.95,.35+k*.45)}/>;
   })}
   {mode==='galaxy'&&<>
    <ellipse cx={540} cy={870} rx={650*zoom} ry={390*zoom} fill="url(#galaxyGlow)" transform={`rotate(${-20+t*.3} 540 870)`}/>
    {galaxies.map((s,i)=>{const q=project(s.x,s.y,s.z);return <circle key={i} cx={q.x} cy={q.y} r={s.r*q.k} fill={Math.hypot(s.x,s.y)<200?'#fff1c9':i%3===0?'#85b8f7':'#cbd5fa'} opacity={.35+rnd(i+7701)*.6}/>;})}
   </>}
   {mode==='cosmic_web'&&<>
    <g stroke="#6c92ee" strokeWidth={10} opacity=".25" filter="url(#filamentGlow)">{edges.map((e,i)=>{const a=project(nodes[e.i].x,nodes[e.i].y,nodes[e.i].z),b=project(nodes[e.j].x,nodes[e.j].y,nodes[e.j].z);return <path key={i} d={`M${a.x} ${a.y} Q${(a.x+b.x)/2+35*Math.sin(i)} ${(a.y+b.y)/2} ${b.x} ${b.y}`} fill="none"/>;})}</g>
    {edges.map((e,i)=>{const a=project(nodes[e.i].x,nodes[e.i].y,nodes[e.i].z),b=project(nodes[e.j].x,nodes[e.j].y,nodes[e.j].z);return <g key={i}>
     <path d={`M${a.x} ${a.y} Q${(a.x+b.x)/2+35*Math.sin(i)} ${(a.y+b.y)/2} ${b.x} ${b.y}`} stroke="#a7c5ff" strokeWidth={.8} opacity=".33" fill="none"/>
     {Array.from({length:7},(_,j)=>{const f=(j+.5)/7;return <circle key={j} cx={a.x*(1-f)+b.x*f+Math.sin(i+j)*7} cy={a.y*(1-f)+b.y*f+Math.cos(i+j)*7} r={.6+rnd(i*7+j)*2} fill="#b8d7ff" opacity=".8"/>;})}
    </g>;})}
    {nodes.map((s,i)=>{const q=project(s.x,s.y,s.z);return <g key={i}><circle cx={q.x} cy={q.y} r={30*q.k} fill="url(#galaxyGlow)"/><circle cx={q.x} cy={q.y} r={2*q.k} fill="#ffeddb"/></g>;})}
   </>}
   {mode==='solar_system'&&<g transform={`translate(540 870) scale(${zoom}) rotate(-18)`}>
    {[200,350,520,730,980].map((r,i)=><g key={r}><ellipse rx={r} ry={r*.43} fill="none" stroke="#8193b0" strokeWidth="1" opacity=".35"/>
      <circle cx={Math.cos(t*(.13-i*.018)+i)*r} cy={Math.sin(t*(.13-i*.018)+i)*r*.43} r={[9,15,18,14,35][i]} fill={['#bdb4a3','#e4bb83','#5497ce','#c97852','#c9ab8c'][i]}/></g>)}
    <circle r={190} fill="url(#sunGlow)"/><circle r={39} fill="#ffe3a1"/>
   </g>}
   {mode==='nebula'&&<g style={{mixBlendMode:'screen'}} opacity=".25">{Array.from({length:9},(_,i)=><ellipse key={i} cx={170+rnd(i+8801)*750+Math.sin(t*.07+i)*70} cy={500+rnd(i+8901)*800} rx={180+rnd(i)*280} ry={300} fill="url(#galaxyGlow)" transform={`rotate(${i*23+t} 540 900)`}/>)}</g>}
  </svg>
  <AbsoluteFill style={{background:'linear-gradient(#0005,transparent 23%,transparent 63%,#0009)'}}/>
 </AbsoluteFill>;
};
