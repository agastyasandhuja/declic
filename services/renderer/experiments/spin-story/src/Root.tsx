import React,{useMemo} from 'react';
import {AbsoluteFill,Audio,Composition,Sequence,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import {PopCaptions} from './PopCaptions';
import {makeTrack,elbow,smooth,mix,WIDE,inertia} from './Motion.mjs';
const C={ink:'#293d4a',teal:'#428f91',skin:'#dfa982',light:'#f2c9a1',hair:'#3c3837',paper:'#fcf4e4',orange:'#d47d51',pants:'#465e7c'};
const Txt=({x=360,y,size=36,c=C.ink,children}:any)=><text x={x} y={y} textAnchor="middle" fontSize={size} fontWeight="bold" fontFamily="DejaVu Sans,sans-serif" fill={c}>{children}</text>;
const Stroke=({d,color=C.ink,width=5,opacity=1}:any)=><path d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" opacity={opacity}/>;
function Defs(){return <defs>
 <linearGradient id="wall" x2="0" y2="1"><stop stopColor="#dce6df"/><stop offset="1" stopColor="#bbcfc9"/></linearGradient>
 <linearGradient id="floor" x2=".6" y2="1"><stop stopColor="#ebd8b8"/><stop offset="1" stopColor="#c5aa87"/></linearGradient>
 <linearGradient id="shirt" x2="1" y2="1"><stop stopColor="#65aaa7"/><stop offset="1" stopColor="#387d85"/></linearGradient>
 <radialGradient id="light"><stop stopColor="#fff9dd" stopOpacity=".6"/><stop offset="1" stopColor="#fff9dd" stopOpacity="0"/></radialGradient>
 </defs>}
function Room({top=false}:any){return <g>
 <rect width={720} height={1280} fill={top?'url(#floor)':'url(#wall)'}/>
 {top?<>
  {Array.from({length:12},(_,i)=><g key={i}><path d={`M0 ${i*120}H720`} stroke="#b69c79" strokeWidth={2} opacity={.55}/><path d={`M${i%2?220:450} ${i*120}v120`} stroke="#b69c79" strokeWidth={2} opacity={.5}/></g>)}
  <rect x={28} y={385} width={664} height={640} rx={180} fill="#829d9b" opacity={.48}/><rect x={44} y={401} width={632} height={608} rx={164} fill="none" stroke="#e4e3cc" strokeWidth={3} opacity={.6}/>
  <rect x={-35} y={40} width={235} height={260} rx={12} fill="#876b54"/><rect x={-35} y={32} width={228} height={253} rx={12} fill="#b68b65"/>
  <rect x={21} y={75} width={128} height={84} rx={6} fill="#3f535d" transform="rotate(-8 80 100)"/><rect x={29} y={84} width={112} height={65} rx={3} fill="#a7ccd0" transform="rotate(-8 80 100)"/><circle cx={147} cy={227} r={20} fill={C.paper}/><circle cx={147} cy={227} r={13} fill="#76513c"/>
 </>:<>
  <rect x={65} y={130} width={250} height={320} rx={10} fill="#a6cbd0" stroke="#f8f2df" strokeWidth={16}/><path d="M190 140v300M75 290h230" stroke="#f8f2df" strokeWidth={12}/>
  <path d="M80 440L300 150v120L170 440Z" fill="#f3f3de" opacity={.25}/><rect y={915} width={720} height={365} fill="url(#floor)"/><path d="M0 914H720" stroke="#91aaa3" strokeWidth={13}/>
  <path d="M0 1090H720M180 920L100 1280M480 920L560 1280" stroke="#b79e7c" strokeWidth={3}/>
  <path d="M40 915V709H224V915" fill="#b18c65"/><path d="M25 711H244" stroke="#775d4a" strokeWidth={18}/><rect x={78} y={616} width={119} height={77} rx={5} fill="#3c535f"/><rect x={87} y={625} width={101} height={59} rx={3} fill="#9fc8ce"/>
  <path d="M580 918L566 836H650L638 918Z" fill="#b87959"/><path d="M609 840V620" stroke="#527f67" strokeWidth={8}/>{[-1,1].map((v,i)=><g key={i}><ellipse cx={609+v*30} cy={680+i*75} rx={24} ry={64} fill={i?'#729c78':'#5f8a71'} transform={`rotate(${v*35} ${609+v*30} ${680+i*75})`}/></g>)}
 </>}
 <ellipse cx={480} cy={300} rx={400} ry={500} fill="url(#light)"/>
 </g>}
function Weight({x,y,angle=0}:any){return <g transform={`translate(${x} ${y}) rotate(${angle})`} stroke={C.ink} strokeWidth={3}><rect x={-6} y={-22} width={12} height={44} rx={5} fill="#9bb2b7"/><rect x={-17} y={-25} width={34} height={12} rx={4} fill={C.orange}/><rect x={-17} y={13} width={34} height={12} rx={4} fill={C.orange}/></g>}
function TopHuman({m,t}:any){
 const a=m.angle*180/Math.PI,scale=280;
 return <g transform="translate(360 720)">
  <ellipse cy={22} rx={155} ry={151} fill="#354a51" opacity={.17}/>
  {/* The five-star base stays on the floor while the seat and seated person rotate. */}
  {[0,72,144,216,288].map(v=><g key={v} transform={`rotate(${v})`}><Stroke d="M0 0L0 137" color="#637983" width={13}/><rect x={-15} y={124} width={30} height={20} rx={8} fill={C.ink}/></g>)}
  <g transform={`rotate(${a})`}>
   <rect x={-103} y={-99} width={206} height={220} rx={66} fill="#344a58" stroke={C.ink} strokeWidth={5}/><rect x={-90} y={-85} width={180} height={192} rx={57} fill="#4c6470"/>
   {[-1,1].map(side=><g key={side}><Stroke d={`M${side*32} 58Q${side*62} 98 ${side*(60+m.feet*35)} 160`} color={C.ink} width={39}/><Stroke d={`M${side*32} 58Q${side*62} 98 ${side*(60+m.feet*35)} 160`} color={C.pants} width={32}/><path d={`M${side*(60+m.feet*35)-19} 151h38v39q-21 15-38-1Z`} fill={C.paper} stroke={C.ink} strokeWidth={4}/></g>)}
   <path d="M-64-27Q0-62 64-27L70 61Q0 104-70 61Z" fill="url(#shirt)" stroke={C.ink} strokeWidth={5}/>
   {[-1,1].map(side=>{const e=elbow(side,m.r),hx=side*m.r*scale,hy=28;return <g key={side}>
    <Stroke d={`M${side*.22*scale} 0L${e[0]*scale} ${e[1]*scale}L${hx} ${hy}`} color={C.ink} width={31}/>
    <Stroke d={`M${side*.22*scale} 0L${e[0]*scale} ${e[1]*scale}`} color={C.teal} width={26}/><Stroke d={`M${e[0]*scale} ${e[1]*scale}L${hx} ${hy}`} color={C.skin} width={23}/>
    <Weight x={hx} y={hy} angle={side*12}/><ellipse cx={hx} cy={hy} rx={12} ry={13} fill={C.light} stroke={C.ink} strokeWidth={3}/>
   </g>})}
   <ellipse cx={0} cy={-32} rx={43} ry={49} fill={C.hair} stroke={C.ink} strokeWidth={4}/><path d="M-34-39Q-20-70 19-65M-28-27Q-10-55 26-49" fill="none" stroke="#635751" strokeWidth={6} strokeLinecap="round"/>
   <ellipse cx={0} cy={16} rx={11} ry={7} fill={C.skin}/>
  </g>
 </g>;
}
function SideHuman({m,t}:any){
 const theta=m.angle,cs=Math.cos(theta),sn=Math.sin(theta);
 const P=(v:number[])=>[360+(v[0]*cs+v[2]*sn)*235,932-v[1]*235+(v[2]*cs-v[0]*sn)*65];
 const line=(pts:number[][])=>pts.map((v,i)=>(i?'L':'M')+P(v).join(' ')).join('');
 const poly=(pts:number[][])=>pts.map(v=>P(v).join(',')).join(' ');
 const head=P([0,1.83,-.02]),seat=P([0,.8,0]),front=cs>0;
 const parts=[-1,1].map(side=>{const e=elbow(side,m.r);return {side,depth:side*sn,arm:[[side*.22,1.46,0],[e[0],1.38,e[1]],[side*m.r,1.29,.1]],leg:[[side*.14,.86,.04],[side*.21,.6,.38],[side*.24,.15*(1-m.feet),.6]]}}).sort((a,b)=>a.depth-b.depth);
 return <g strokeLinejoin="round" strokeLinecap="round">
  <ellipse cx={360} cy={946} rx={168} ry={33} fill="#30434c" opacity={.15}/><Stroke d="M360 941V745" color="#627b86" width={17}/>
  {[-1,1].map(i=><g key={i}><Stroke d={`M360 933L${360+i*111} 954`} color="#526975" width={15}/><ellipse cx={360+i*111} cy={961} rx={18} ry={12} fill={C.ink}/></g>)}
  <ellipse cx={seat[0]} cy={seat[1]} rx={106} ry={30} fill="#45606f" stroke={C.ink} strokeWidth={5}/>
  {parts.map(({side,leg})=><g key={side}><Stroke d={line(leg)} color={C.ink} width={36}/><Stroke d={line(leg)} color={C.pants} width={29}/><ellipse cx={P(leg[2])[0]+10*cs} cy={P(leg[2])[1]} rx={29} ry={12} fill={C.paper} stroke={C.ink} strokeWidth={4}/></g>)}
  <path d={`M${360-(45+20*Math.abs(cs))} 584Q360 566 ${360+(45+20*Math.abs(cs))} 584L${360+(41+16*Math.abs(cs))} 727Q360 747 ${360-(41+16*Math.abs(cs))} 727Z`} fill="url(#shirt)" stroke={C.ink} strokeWidth={5}/>
  {parts.map(({side,arm})=><g key={side}><Stroke d={line(arm)} color={C.ink} width={29}/><Stroke d={line(arm.slice(0,2))} color={C.teal} width={24}/><Stroke d={line(arm.slice(1))} color={C.skin} width={21}/><Weight x={P(arm[2])[0]} y={P(arm[2])[1]}/><ellipse cx={P(arm[2])[0]} cy={P(arm[2])[1]} rx={12} ry={11} fill={C.light} stroke={C.ink} strokeWidth={3}/></g>)}
  <g transform={`translate(${head[0]} ${head[1]})`}>
   <path d="M-17 58V80H17V58" fill={C.skin} stroke={C.ink} strokeWidth={4}/><ellipse rx={46} ry={57} fill={front?C.light:C.hair} stroke={C.ink} strokeWidth={4}/>
   <path d="M-44 2Q-58-48-25-59Q13-78 42-49L48-15Q16-34 9-47Q-7-22-39-24Z" fill={C.hair}/>
   {front&&<g transform={`scale(${Math.max(.18,Math.abs(cs))} 1)`}><path d="M-27 0l15-3M10-3l15 3" stroke={C.ink} strokeWidth={4}/><ellipse cx={-18} cy={11} rx={4} ry={(t%3.8)<.1?1:6} fill={C.ink}/><ellipse cx={18} cy={11} rx={4} ry={(t%3.8)<.1?1:6} fill={C.ink}/><path d="M-10 37Q0 44 12 36" stroke="#895345" strokeWidth={3} fill="none"/></g>}
  </g>
 </g>;
}
function Science({scene,m,u}:any){
 const ratioI=m.I/inertia(WIDE),ratioW=m.omega/1.35;
 if(['hook','above','outro'].includes(scene))return null;
 return <g><rect x={64} y={100} width={592} height={260} rx={24} fill={C.paper} opacity={.96}/>
  {scene==='isolated'?<><Txt y={171} size={35}>τ ≈ 0</Txt><Txt y={252} size={48}>L = Iω</Txt><Txt y={313} size={24}>L ≈ constant</Txt></>:
   scene==='energy'?<><Txt y={172} size={32}>W = ΔK</Txt><Txt y={240} size={35}>K = ½ Iω²</Txt><rect x={200} y={278} width={320} height={24} rx={8} fill="#dedacb"/><rect x={200} y={278} width={320*smooth(u/.6)} height={24} rx={8} fill={C.orange}/><Txt y={334} size={21}>Muscular work → kinetic energy</Txt></>:
   scene==='brake'?<><Txt y={180} size={34}>τ ≠ 0</Txt><Txt y={246} size={37}>L ↓</Txt><rect x={180} y={282} width={360} height={22} rx={8} fill="#dedacb"/><rect x={180} y={282} width={360*m.L/(inertia(WIDE)*1.35)} height={22} rx={8} fill={C.orange}/></>:
   <><Txt y={163} size={37}>L = Iω</Txt><Txt x={148} y={231} size={29}>I</Txt><rect x={189} y={205} width={280*ratioI} height={30} rx={7} fill={C.teal}/><Txt x={562} y={232} size={27}>{ratioI.toFixed(2)}×</Txt><Txt x={148} y={301} size={29}>ω</Txt><rect x={189} y={275} width={140*ratioW} height={30} rx={7} fill={C.orange}/><Txt x={562} y={302} size={27}>{ratioW.toFixed(2)}×</Txt></>}
 </g>;
}
const Movie=({lesson}:{lesson:any})=>{
 const f=useCurrentFrame(),t=f/30,track=useMemo(()=>makeTrack(lesson),[lesson]),m=track(t);
 const b=lesson.segments.find((s:any)=>t>=s.start&&t<s.end)||lesson.segments.at(-1),u=(t-b.start)/(b.end-b.start),top=!['hook','outro'].includes(b.scene);
 return <AbsoluteFill><svg viewBox="0 0 720 1280" style={{width:720,height:1280}}><Defs/><Room top={top}/>
  {top?<TopHuman m={m} t={t}/>:<SideHuman m={m} t={t}/>}
  <Science scene={b.scene} m={m} u={u}/>
  {b.scene==='above'&&u<.5&&<g opacity={1-smooth(u*2)}><path d="M365 200L330 230l35 30V200M410 200L375 230l35 30Z" fill={C.ink}/></g>}
 </svg><PopCaptions words={lesson.words} now={t} top={1070}/>
 {lesson.segments.map((s:any,i:number)=><Sequence key={i} from={Math.round(s.start*30)} durationInFrames={Math.ceil(s.duration*30)}><Audio src={staticFile(`${lesson.id}/assets/${s.audio}`)}/></Sequence>)}
 <Audio src={staticFile(`${lesson.id}/assets/ambience.wav`)} volume={.3}/>
 </AbsoluteFill>;
};
registerRoot(()=> <Composition id="Story" component={Movie} width={720} height={1280} fps={30} durationInFrames={1500} calculateMetadata={({props})=>({durationInFrames:props.lesson.frames})}/>);
