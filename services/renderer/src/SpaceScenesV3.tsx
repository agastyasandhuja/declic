import React from 'react';
import {AbsoluteFill,useCurrentFrame} from 'remotion';
import {BiologyScenes, BIOLOGY_MODES} from './BiologyScenes';
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const ease=(x:number)=>{x=clamp(x);return x*x*(3-2*x)};
const mixPosition=(a:number,b:number,p:number)=>a+(b-a)*p;
const random=(i:number)=>{const n=Math.sin(i*127.1+311.7)*43758.5453;return n-Math.floor(n)};
const baseHubs=[[170,640],[790,540],[490,900],[190,1220],[850,1220],[610,1440]];
const links=[[0,1],[0,2],[1,2],[1,4],[2,3],[2,4],[3,5],[4,5]];
const Label=({x,y,children,color='#d6e6ff'}:any)=><text x={x} y={y} textAnchor="middle" fill={color} fontFamily="DejaVu Sans" fontSize="32">{children}</text>;

// Each mode has its own geometry and explanatory motion. No shared spinning mesh.
export const SpaceScenesV3=({shot}:{shot:any})=>{
 const t=useCurrentFrame()/30,age=t-shot.start,p=clamp(age/(shot.end-shot.start)),e=ease(p),mode=shot.space_mode;
 if(BIOLOGY_MODES.has(mode)) return <BiologyScenes shot={shot}/>;
 const seed=[...shot.shot_id].reduce((n:number,c:string)=>n+c.charCodeAt(0),0);
 const hubs=baseHubs.map(([x,y],i)=>[x+(random(seed+i)-.5)*130,y+(random(seed+i+20)-.5)*130]);
 return <AbsoluteFill style={{background:'radial-gradient(ellipse at 45% 40%,#10162f,#01030a 72%)'}}>
 <svg viewBox="0 0 1080 1920" width="1080" height="1920">
 <defs>
  <radialGradient id="glow"><stop stopColor="#fff5dc"/><stop offset=".12" stopColor="#cab6ff" stopOpacity=".85"/><stop offset="1" stopColor="#506fff" stopOpacity="0"/></radialGradient>
  <radialGradient id="sun"><stop stopColor="#fff8cc"/><stop offset=".3" stopColor="#ffd36a"/><stop offset="1" stopColor="#e98b18" stopOpacity="0"/></radialGradient>
  <radialGradient id="earth"><stop stopColor="#62e6da"/><stop offset=".6" stopColor="#2875b7"/><stop offset="1" stopColor="#071323"/></radialGradient>
 </defs>
 <g transform="translate(0 100) scale(1 .8)">
 {Array.from({length:120},(_,i)=><circle key={i} cx={random(i)*1080} cy={random(i+200)*1920} r={.6+random(i+400)*1.5} fill="#ccddff" opacity={.13+random(i+600)*.35}/>)}
 {mode==='galaxy'&&<g transform={`translate(540 920) rotate(${-30+e*24}) scale(${.86+e*.22} .64)`}>
  <circle r="310" fill="url(#glow)"/>
  {Array.from({length:360},(_,i)=>{const radius=30+Math.sqrt(random(i))*450,theta=radius*.013+(i%3)*Math.PI*2/3+(random(i+2)-.5)*.6;return <ellipse key={i} cx={Math.cos(theta)*radius} cy={Math.sin(theta)*radius} rx={1.3+random(i+4)*3} ry="2" fill={i%5?'#c9d9ff':'#f6d9b6'} opacity={.35+random(i+5)*.65}/>})}
  <circle r="35" fill="url(#sun)"/>
 </g>}
 {mode==='gravity'&&<>
  {hubs.slice(0,4).map(([x,y],i)=><g key={i}><circle cx={x} cy={y+120} r={90+e*65} fill="url(#glow)"/><circle cx={x} cy={y+120} r={5+e*8} fill="#f4e7ff"/></g>)}
  {Array.from({length:150},(_,i)=>{const [hx,hy]=hubs[i%4],sx=random(i+900)*950+65,sy=600+random(i+1100)*800,q=e*.87;const x=sx+(hx-sx)*q,y=sy+(hy+120-sy)*q;return <g key={i}><path d={`M${sx} ${sy} L${x} ${y}`} stroke="#8fb9ff" strokeWidth="1.2" opacity={.12}/><circle cx={x} cy={y} r={2.3} fill="#bfdbff"/></g>})}
  <Label x={540} y={1370}>Matter gathers under gravity</Label>
 </>}
 {mode==='cosmic_web'&&<g transform={`translate(${(1-e)*40} ${(1-e)*-30}) scale(${.94+e*.06})`}>
  {links.map(([a,b],i)=>{const [x,y]=hubs[a],[xx,yy]=hubs[b];return <g key={i}><path d={`M${x} ${y} Q${(x+xx)/2+30} ${(y+yy)/2-30} ${xx} ${yy}`} stroke="#8a82d8" strokeWidth="17" opacity=".08" fill="none"/>{Array.from({length:28},(_,j)=>{const f=(j+.5)/28;return <ellipse key={j} cx={x*(1-f)+xx*f+(random(i*100+j)-.5)*35} cy={y*(1-f)+yy*f+(random(i*100+j+40)-.5)*35} rx={2.3} ry={1.5} fill={j%4?'#c0cfff':'#ffe7bd'} opacity={clamp(e*5-j/35)}/>})}</g>})}
  {hubs.map(([x,y],i)=><g key={i}><circle cx={x} cy={y} r="75" fill="url(#glow)"/>{Array.from({length:13},(_,j)=><ellipse key={j} cx={x+(random(j+i*41)-.5)*65} cy={y+(random(j+i*21)-.5)*65} rx="3" ry="1.8" fill="#f4e6ff"/>)}</g>)}
  {shot.start>0&&<><Label x={680} y={1030}>void</Label><Label x={300} y={1370}>galaxies trace filaments</Label></>}
 </g>}
 {mode==='scale_ladder'&&<>
  {[{x:260,y:690,r:58,label:'Stars',c:'#ffda9b'},{x:540,y:990,r:135,label:'Galaxies',c:'#b5c9ff'},{x:430,y:1270,r:155,label:'Groups + clusters',c:'#a393ef'}].map((a,i)=><g key={i} opacity={ease(p*3-i*.65)} transform={`translate(0 ${(1-ease(p*3-i*.65))*55})`}>
   {i===0?<circle cx={a.x} cy={a.y} r={a.r} fill="url(#sun)"/>:Array.from({length:i===1?70:22},(_,j)=>{const r=random(j+20)*a.r,ang=random(j)*Math.PI*2;return <ellipse key={j} cx={a.x+Math.cos(ang)*r} cy={a.y+Math.sin(ang)*r*.5} rx={i===1?2:9} ry={i===1?2:3} fill={a.c} transform={`rotate(-15 ${a.x} ${a.y})`}/>})}
   <Label x={i===2?760:a.x+165} y={a.y+12}>{a.label}</Label>
  </g>)}
  <path d="M260 720 C270 820 440 870 490 950 M540 1040 C550 1130 450 1140 440 1220" fill="none" stroke="#8191b7" strokeWidth="2" strokeDasharray="6 12"/>
 </>}
 {mode==='filament_detail'&&<>
  {Array.from({length:12},(_,i)=>{const x=180+i*65,y=710+i*34+Math.sin(i)*25,r=8+e*18;
   return <g key={i} transform={`translate(${x} ${y}) rotate(-25)`}><ellipse rx={r*2.5} ry={r*.7} fill="url(#glow)"/><ellipse rx={r} ry={r*.3} fill="#e2dcff" opacity=".8"/><ellipse rx={r*.4} ry={r*.2} fill="#fff5dc"/></g>})}
  <Label x={540} y={1230}>Galaxies along a filament</Label>
  <Label x={540} y={1320}>Matter, not a solid string</Label>
 </>}
 {mode==='cosmic_sheet'&&<>
  {Array.from({length:35},(_,i)=><ellipse key={i} cx={150+i*23} cy={620+Math.sin(i*.16)*40} rx={3.3} ry={1.8} fill="#fce0b6"/>)}
  <Label x={540} y={540}>Filament</Label>
  {Array.from({length:220},(_,i)=>{const x=160+(i%20)*38,y=710+Math.floor(i/20)*40,noise=(random(i+seed)-.5)*22;
   return <ellipse key={i} cx={mixPosition(random(i)*1080,x+noise,e)} cy={mixPosition(500+random(i+50)*800,y+(x-540)*.25+noise,e)} rx={3} ry={1.6} fill={i%4?'#b8caff':'#ffe0b4'}/>})}
  <Label x={540} y={1320}>Galaxies trace sheets</Label>
 </>}
 {mode==='cosmic_overview'&&<>
  {Array.from({length:15},(_,i)=>{const angle=i*Math.PI*2/15,x=540+Math.cos(angle)*360,y=930+Math.sin(angle)*350;
   const j=(i+4)%15,xx=540+Math.cos(j*Math.PI*2/15)*360,yy=930+Math.sin(j*Math.PI*2/15)*350;
   return <g key={i}><circle cx={x} cy={y} r={45} fill="url(#glow)"/>{Array.from({length:20},(_,k)=>{const q=k/20;return <ellipse key={k} cx={x*(1-q)+xx*q} cy={y*(1-q)+yy*q} rx={1.6} ry={1} fill="#a4b7ec" opacity={.3+e*.6}/>})}</g>})}
  <Label x={540} y={940}>void</Label><Label x={540} y={1370}>Filaments surround emptier regions</Label>
 </>}
 {mode==='solar_system' &&<g transform="translate(540 980) rotate(-18)">
  {[160,265,390,510].map((r,i)=><g key={r}><ellipse rx={r} ry={r*.5} stroke="#8ca1cb" opacity=".4" fill="none"/><circle cx={Math.cos(age*(.7-i*.12)+i)*r} cy={Math.sin(age*(.7-i*.12)+i)*r*.5} r={12+i*4} fill={['#b5b5be','#d7a674','#64a5e0','#c27761'][i]}/></g>)}<circle r="115" fill="url(#sun)"/><circle r="30" fill="#ffe7a9"/>
 </g>}
 {['light_travel','lookback'].includes(mode)&&<>
  <circle cx="200" cy="850" r="130" fill="url(#sun)"/><circle cx="840" cy="850" r="65" fill="url(#earth)"/>
  <path d="M240 850 H770" stroke="#fff2b6" opacity=".3" strokeDasharray="7 13"/>
  {[0,1,2].map(i=>{const q=mode==='lookback'?(p*1.5+i/3)%1:p;return <g key={i} opacity={mode==='light_travel'?(i===0?1:0):1}><circle cx={250+q*510} cy="850" r="40" fill="url(#sun)"/><circle cx={250+q*510} cy="850" r="6" fill="#fff8da"/></g>})}
  <Label x={200} y={1050}>emitted earlier</Label><Label x={800} y={1050}>received now</Label>
  {mode==='lookback'&&<><path d="M160 1250 H900" stroke="#8c9cb7" strokeWidth="2"/><circle cx={160+e*740} cy="1250" r="10" fill="#c9a8ff"/><Label x={540} y={1370}>Light carries an earlier view</Label></>}
 </>}
 {mode==='nebula'&&Array.from({length:18},(_,i)=><ellipse key={i} cx={200+random(i)*650+Math.sin(age*.13+i)*70} cy={650+random(i+40)*650} rx={130+random(i+99)*180} ry={140} fill="url(#glow)" opacity=".25" transform={`rotate(${i*21} 540 950)`}/>)}
 {mode==='starfield'&&Array.from({length:100},(_,i)=>{const angle=random(i)*Math.PI*2,r=40+((random(i+1)*600+age*65)%700);return <path key={i} d={`M${540+Math.cos(angle)*r} ${950+Math.sin(angle)*r} l${Math.cos(angle)*r*.06} ${Math.sin(angle)*r*.06}`} stroke="#bdcfff" opacity={r/1000}/>})}
 </g>
 </svg>
 </AbsoluteFill>;
};
