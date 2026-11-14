import {PopCaptions} from './PopCaptions';
import React from 'react';
import {AbsoluteFill, Audio, Composition, Sequence, registerRoot, staticFile, useCurrentFrame} from 'remotion';

const C={ink:'#eef4ff',muted:'#8797b2',cyan:'#63e4e5',yellow:'#ffe367',pink:'#ff729f',blue:'#819dff',dark:'#101a2e'};
const clamp=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(v:number)=>{const x=clamp(v);return x*x*(3-2*x);};
const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
const T=({x=500,y=100,size=38,color=C.ink,children,anchor='middle',...rest}:any)=>{
 const text=React.Children.toArray(children).join('');
 const available=anchor==='start'?940-x:900;
 const fit=Math.min(size,available/Math.max(1,text.length*.64));
 return <text x={x} y={y} fill={color} fontSize={fit} textAnchor={anchor} fontFamily="DejaVu Sans,sans-serif" fontWeight="700" {...rest}>{children}</text>;
};
const Line=({x1,y1,x2,y2,color=C.muted,width=6,...rest}:any)=><line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={width} strokeLinecap="round" {...rest}/>;
const Dot=({x,y,r=25,color=C.cyan}:any)=><circle cx={x} cy={y} r={r} fill={color}/>;
const Box=({x,y,w=150,h=100,color=C.cyan,children}:any)=><g><rect x={x} y={y} width={w} height={h} rx={18} fill={color} fillOpacity={.12} stroke={color} strokeWidth={4}/>{children}</g>;
const Cube=({x,y,size=130,color=C.cyan}:any)=><g transform={`translate(${x} ${y})`}><path d={`M0 0 l${size} 0 0 ${size} -${size} 0 Z`} fill={color}/><path d={`M0 0 l${size*.35} -${size*.25} ${size} 0 -${size*.35} ${size*.25} Z`} fill={color} opacity={.7}/><path d={`M${size} 0 l${size*.35} -${size*.25} 0 ${size} -${size*.35} ${size*.25} Z`} fill={color} opacity={.45}/></g>;
const Face=({x,y,color=C.cyan,name='',talk=false,sad=false,size=85}:any)=><g transform={`translate(${x} ${y})`}><circle r={size} fill={color}/><circle cx={-size*.3} cy={-size*.15} r={size*.08} fill="#101a2e"/><circle cx={size*.3} cy={-size*.15} r={size*.08} fill="#101a2e"/>{talk?<ellipse cx={0} cy={size*.32} rx={size*.16} ry={size*.19} fill="#101a2e"/>:<path d={sad?`M${-size*.25} ${size*.38} Q0 ${size*.05} ${size*.25} ${size*.38}`:`M${-size*.25} ${size*.2} Q0 ${size*.55} ${size*.25} ${size*.2}`} fill="none" stroke="#101a2e" strokeWidth={7} strokeLinecap="round"/>}{name&&<T y={size+54} size={32} x={0}>{name}</T>}</g>;

function Waves({s,u,t}:any){
 const path=(offset:number,amp:number,phase=0)=>Array.from({length:121},(_,i)=>`${i?'L':'M'}${70+i*7.1},${offset+amp*Math.sin(i/9-t*3+phase)}`).join(' ');

 return <g><T y={65} size={30} color={C.muted}>IDEAL SIGNALS AT ONE LOCATION</T><path d={path(240,90)} stroke={C.cyan} strokeWidth={10} fill="none"/><T x={70} y={100} anchor="start" size={30} color={C.cyan}>UNWANTED SOUND</T>{s>=1&&<><path d={path(500,90,Math.PI)} stroke={C.pink} strokeWidth={10} fill="none"/><T x={70} y={385} anchor="start" size={30} color={C.pink}>OPPOSITE WAVE</T></>}<Line x1={70} y1={690} x2={925} y2={690} width={2}/><path d={path(820,0)} stroke={s>=2?C.yellow:C.muted} strokeWidth={s>=2?12:3} strokeDasharray={s>=2?undefined:"10 16"} fill="none"/>{s===3&&<><Line x1={500} y1={170} x2={500} y2={870} width={3} color={C.ink} strokeDasharray="8 12"/><T y={990} size={32}>LISTENING POINT ↑</T></>}<T x={70} y={715} anchor="start" size={30} color={C.yellow}>{s>=2?'SUM: CANCELLATION':'WHAT WILL THE SUM DO?'}</T></g>;
}
function Puck({s,u,t}:any){
 if(s===3)return <g><Line x1={100} y1={650} x2={900} y2={650} width={18}/><path d="M330 310 H490 V470 Q680 460 740 590 V630 H300 V480 Z" fill={C.blue}/><Line x1={420} y1={700} x2={170} y2={700} color={C.pink} width={12}/><path d="M195 675 L165 700 195 725" fill="none" stroke={C.pink} strokeWidth={12}/><Line x1={490} y1={540} x2={850} y2={540} color={C.cyan} width={12}/><path d="M825 515 L855 540 825 565" fill="none" stroke={C.cyan} strokeWidth={12}/><T y={160} size={45} color={C.cyan}>FRICTION GIVES YOU TRACTION</T><T y={810} size={36} color={C.pink}>YOUR FOOT PUSHES THE FLOOR BACK</T><T y={900} size={36} color={C.cyan}>THE FLOOR PUSHES YOU FORWARD</T></g>;
 const x=s===0?300:s===1?mix(300,560,u):mix(560,730,1-Math.pow(1-u,2));
 return <g><path d="M50 720 L300 310 L830 310 L970 720 Z" fill="#152640" stroke="#2d4360" strokeWidth={4}/>{Array.from({length:9},(_,i)=><Line key={i} x1={120+i*95} y1={710} x2={320+i*62} y2={330} width={2} color="#30415c"/>)}<ellipse cx={x} cy={555} rx={95} ry={35} fill={C.cyan}/><path d={`M${x-95} 555 v32 a95 35 0 0 0 190 0 v-32`} fill="#33989c"/>{s===1&&<g><Line x1={x-130} y1={560} x2={x-210} y2={560} color={C.cyan}/><Line x1={x-140} y1={590} x2={x-200} y2={590} color={C.cyan}/></g>}{s===2&&Array.from({length:12},(_,i)=><Dot key={i} x={x-60-i*17} y={620+Math.sin(i*3+t)*20} r={5+u*5} color={C.pink}/>)}<T y={850} size={53} color={s===2?C.pink:C.cyan}>{s===2?'MOTION → THERMAL ENERGY':s===0?'AT REST':'CONSTANT VELOCITY'}</T><T y={130} color={C.muted} size={32}>IDEALIZED HORIZONTAL MOTION</T></g>;
}
const routeA=[[150,730],[300,520],[480,340],[800,180]];
const routeB=[[150,730],[700,800],[850,620],[900,380],[800,180]];
function MapScene({s,u}:any){
 const pts=(arr:number[][])=>arr.map(p=>p.join(',')).join(' ');
 const draw=(arr:number[][],color:string,cost:string,show:boolean)=> <g opacity={show?1:.22}><polyline points={pts(arr)} stroke={color} strokeWidth={19} strokeLinejoin="round" fill="none"/>{(s===1&&arr===routeA||s===2&&arr===routeB)&&<polyline points={pts(arr)} pathLength={1} stroke={C.yellow} strokeWidth={8} strokeLinejoin="round" fill="none" strokeDasharray={`${clamp(u/.85)} 1`}/>} {arr.map(([x,y],i)=><g key={i}><Dot x={x} y={y} r={15} color={color}/>{i>0&&show&&<T x={arr===routeB&&i===4?905:(x+arr[i-1][0])/2-32} y={arr===routeB&&i===4?285:(y+arr[i-1][1])/2-22} size={33} color={color}>{cost}</T>}</g>)}</g>;
 return <g><rect x={40} y={60} width={920} height={850} rx={30} fill="#142b2a"/>{Array.from({length:10},(_,i)=><g key={i}><Line x1={40+i*100} y1={60} x2={40+i*100} y2={910} color="#28433e" width={2}/><Line x1={40} y1={60+i*90} x2={960} y2={60+i*90} color="#28433e" width={2}/></g>)}<path d="M50 150 Q350 350 500 650 T950 900" fill="none" stroke="#254e65" strokeWidth={85}/>{draw(routeA,C.pink,'4',s!==2)}{draw(routeB,C.cyan,'2',s>=2)}<Dot x={150} y={730} r={28} color={C.yellow}/><Dot x={800} y={180} r={28} color={C.yellow}/><T x={180} y={810} size={29}>START</T><T x={770} y={120} size={29}>CLASS</T><T y={995} size={31} color={C.muted}>FICTIONAL MAP · EDGE LABELS ARE MINUTES</T>{s===3&&<Box x={115} y={155} w={330} h={120}><T x={280} y={235} size={65} color={C.cyan}>8 &lt; 12</T></Box>}</g>;
}
function MathScene({s,u}:any){
 const p=ease(u/.7),value=s===0?3:s===1?mix(3,-3,p):s===2?mix(-3,3,p):3;
 const x=500+value*120;
 return <g><T y={160} size={80} color={s===1?C.pink:C.cyan}>{s===0?'+3':s===1?'× (−1)':'× (−1) AGAIN'}</T><Line x1={60} y1={530} x2={940} y2={530} color={C.ink}/>{Array.from({length:7},(_,i)=><g key={i}><Line x1={140+i*120} y1={510} x2={140+i*120} y2={550}/><T x={140+i*120} y={610} size={38}>{i-3}</T></g>)}<Line x1={500} y1={250} x2={500} y2={750} color={C.muted} width={2} strokeDasharray="12 14"/>{s>0&&<path d={s===1?'M860 480 Q500 60 140 480':'M140 480 Q500 60 860 480'} stroke={C.blue} strokeWidth={5} fill="none" strokeDasharray="10 15"/>}<Dot x={x} y={s===1||s===2?480-Math.sin(p*Math.PI)*260:480} r={42} color={s===1?C.pink:C.cyan}/><T y={855} size={54}>{s===3?'−(−3) = 3':'REFLECT THROUGH ZERO'}</T></g>;
}
function Gravity({s,u,t}:any){
 const y=s===0?380:s===1?mix(620,230,ease(u/.75)):s===2?mix(230,620,ease(u/.8)):620;
 return <g><path d="M180 850 V140 H760 V850" fill="none" stroke="#3e506e" strokeWidth={38}/><Line x1={480} y1={150} x2={480} y2={y} color={C.ink} width={8}/><circle cx={480} cy={145} r={62} fill={C.dark} stroke={C.yellow} strokeWidth={12}/><g transform={`rotate(${t*(s===2?-90:90)} 480 145)`}><Line x1={435} y1={145} x2={525} y2={145} color={C.yellow}/></g><Cube x={385} y={y} size={180} color={C.blue}/><Line x1={95} y1={810} x2={905} y2={810} width={12}/><path d="M540 145 H785 V580" fill="none" stroke={C.yellow} strokeWidth={7} strokeDasharray="14 9"/><Box x={650} y={580} w={270} h={150} color={C.yellow}><T x={785} y={650} size={30} color={C.yellow}>{s===1?'MOTOR':s===2?'GENERATOR':'STORAGE'}</T><T x={785} y={700} size={37}>{s===2?'OUT ↓':s===1?'IN ↑':'⇅'}</T></Box><T y={970} size={51} color={C.cyan}>{s===3?'ENERGY OUT < ENERGY IN':'ENERGY = MASS × GRAVITY × HEIGHT'}</T></g>;
}
function Money({s,u}:any){
 const period=s===0?0:s===1?Math.min(3,Math.floor(u*4)):s===2?Math.min(3,Math.floor(u*4)):3;
 const a=100+period*10,b=100*Math.pow(1.1,period);
 return <g><T y={80} size={30} color={C.muted}>HYPOTHETICAL · 10% PER PERIOD</T><T y={220} size={50}>PERIOD {period}</T><rect x={160} y={800-a*3.4} width={240} height={a*3.4} rx={15} fill={C.blue}/><rect x={590} y={800-b*3.4} width={240} height={b*3.4} rx={15} fill={C.cyan}/><T x={280} y={765-a*3.4} size={53}>${a.toFixed(2)}</T><T x={710} y={765-b*3.4} size={53}>${b.toFixed(2)}</T><T x={280} y={870} size={36} color={C.blue}>SIMPLE</T><T x={710} y={870} size={36} color={C.cyan}>COMPOUND</T><T y={990} size={45}>{s===3?'GROWTH ON EARLIER GROWTH':'SAME $100 START'}</T></g>;
}
function Balls({s,u,t,predict=false}:any){
 const fall=s===2?clamp(u/.65):s===3?1:0;
 const y=220+520*fall*fall;
 return <g><rect x={100} y={100} width={800} height={710} rx={50} fill="#111f36" stroke="#4d627e" strokeWidth={4}/><T y={60} size={31} color={C.muted}>VACUUM · AIR RESISTANCE EXCLUDED</T><Line x1={500} y1={135} x2={500} y2={785} width={2} strokeDasharray="10 20"/><circle cx={300} cy={y} r={55} fill={C.cyan}/><circle cx={700} cy={y} r={55} fill={C.pink}/><T x={300} y={y+12} size={32} color="#0c1830">1 kg</T><T x={700} y={y+12} size={32} color="#0c1830">10 kg</T><Line x1={125} y1={800} x2={875} y2={800} color={C.ink} width={8}/>{s===0&&predict?<g><circle cx={500} cy={955} r={85} fill="none" stroke={C.yellow} strokeWidth={9} strokeDasharray={`${Math.max(0,1-u)*534} 534`} transform="rotate(-90 500 955)"/><T y={968} size={30} color={C.yellow}>GUESS</T></g>:<T y={950} size={s===3?70:43} color={s===3?C.cyan:C.ink}>{s===3?'SAME FALL TIME':s===0?'DOES MASS CHANGE THE FALL?':s===1?'SAME HEIGHT · START AT REST':'y = ½gt²'}</T>}</g>;
}
function Circuit({s,u,t}:any){
 const closed=s===2;
 const pts=[[220,280],[800,280],[800,730],[220,730],[220,280]];
 const point=(v:number)=>{const k=v*4,i=Math.floor(k)%4,p=k%1;return [mix(pts[i][0],pts[i+1][0],p),mix(pts[i][1],pts[i+1][1],p)];};
 return <g>{s===0&&<rect x={100} y={155} width={800} height={690} rx={70} fill="#1b2b45" stroke={C.blue} strokeWidth={8}/>}<path d="M220 400 V280 H460 M610 280 H800 V730 H220 V570" fill="none" stroke={closed?C.cyan:C.muted} strokeWidth={14}/><Line x1={460} y1={280} x2={610} y2={closed?280:180} color={C.yellow} width={13}/><Dot x={460} y={280} r={16} color={C.yellow}/><Dot x={610} y={280} r={16} color={C.yellow}/><rect x={150} y={400} width={140} height={170} rx={15} fill={C.blue}/><T x={220} y={453} size={46}>+</T><T x={220} y={542} size={46}>−</T><circle cx={800} cy={520} r={90} fill={closed?C.yellow:'#17253e'} stroke={closed?C.yellow:C.muted} strokeWidth={7}/><path d="M760 550 l25 -50 30 45 25 -50" fill="none" stroke={closed?'#a66f17':C.muted} strokeWidth={9}/>{closed&&Array.from({length:12},(_,i)=>{const [x,y]=point((i/12+t*.17)%1);return x<300&&y>365&&y<600?null:<Dot key={i} x={x} y={y} r={9} color={C.yellow}/>;})}<T y={930} size={45}>{closed?'CURRENT NEEDS A COMPLETE PATH':s===0?'FIND THE GAP':s===1?'A COMPLETE LOOP IS REQUIRED':'OPEN SWITCH → NO STEADY CURRENT'}</T><T y={1010} size={25} color={C.muted}>DOTS INDICATE CONVENTIONAL CURRENT · NOT TO SCALE</T></g>;
}
function Grid({count=16,x=75,y=260,w=850,h=530,active=16,color=C.cyan,target=15,scramble=false}:any){return <g>{Array.from({length:count},(_,i)=>{const cols=4,xx=x+i%cols*w/cols,yy=y+Math.floor(i/cols)*h/4;return <g key={i} opacity={i>=16-active?1:.12}><rect x={xx} y={yy} width={w/cols-20} height={h/4-20} rx={15} fill={i===target&&active===1?C.yellow:color} fillOpacity={.18} stroke={i===target&&active===1?C.yellow:color} strokeWidth={3}/><T x={xx+(w/cols-20)/2} y={yy+(h/4-20)/2+14} size={37}>{scramble?(i*7+5)%16+1:i+1}</T></g>;})}</g>;}
function Search({s,u,versus=false}:any){
 const step=s<2?0:Math.min(4,Math.floor(u*5)),active=s===3?1:16/2**step;
 if(versus){
  const scan=s===0?0:s===1?Math.min(16,Math.floor(u*17)):16;
  return <g><T x={250} y={200} size={60} color={C.pink}>SCAN</T><T x={750} y={200} size={60} color={C.cyan}>SPLIT</T><Line x1={500} y1={140} x2={500} y2={900} width={2}/><g transform="translate(10 180) scale(.48)"><Grid color={C.pink}/>{scan>0&&<rect x={75+((scan-1)%4)*212.5} y={260+Math.floor((scan-1)/4)*132.5} width={192.5} height={112.5} rx={15} fill={C.yellow} fillOpacity={.6}/>}</g><g transform="translate(510 180) scale(.48)"><Grid active={active}/></g><T x={250} y={760} size={100} color={C.pink}>{scan}</T><T x={750} y={760} size={100} color={C.cyan}>{s===3?4:step}</T><T x={250} y={825} size={32}>CHECKS</T><T x={750} y={825} size={32}>SPLITS</T><T y={980} size={37} color={C.yellow}>{s===3?'SPLITTING REQUIRES ORDER':'SAME TARGET: BOX 16'}</T></g>;
 }
 return <g><T y={100} size={47} color={C.yellow}>{s===0?'FIND THE FINAL BOX':s===1?'CHECK EACH CANDIDATE':s===2?'KEEP THE CORRECT HALF':'ONE CANDIDATE REMAINS'}</T><Grid active={active} scramble={s===1}/>{s===1&&<rect x={75+(Math.min(15,Math.floor(u*16))%4)*212.5} y={260+Math.floor(Math.min(15,Math.floor(u*16))/4)*132.5} width={192.5} height={112.5} rx={15} fill="none" stroke={C.yellow} strokeWidth={9}/>}<T y={910} size={70} color={C.cyan}>{s<2?'16 CANDIDATES':`${s===3?4:step} SPLITS · ${active} LEFT`}</T><T y={1000} size={31} color={C.muted}>{s===1?'UNORDERED: CHECK ONE BY ONE':'BALANCED PARTITIONS OF ORDERED SLOTS'}</T></g>;
}
function Lists({s,u,conversation=false}:any){
 const copied=s===3;
 const row=(x:number,y:number,vals:string,color:string)=> <Box x={x} y={y} w={380} h={130} color={color}><T x={x+190} y={y+85} size={56}>{vals}</T></Box>;
 return <g>{conversation&&<><Face x={155} y={120} size={58} color={C.cyan} talk={s%2===0}/><Face x={845} y={120} size={58} color={C.pink} talk={s%2===1}/><Box x={250} y={30} w={500} h={175} color={s%2===0?C.cyan:C.pink}><T x={500} y={105} size={27}>{s===0?'“WHY DID BOTH CHANGE?”':s===1?'“ONE LIST. TWO NAMES.”':s===2?'“OH. SAME OBJECT.”':'“MAKE AN ACTUAL COPY.”'}</T></Box></>}<T x={200} y={350} size={75} color={C.cyan}>a</T><T x={800} y={350} size={75} color={C.pink}>b</T><path d={copied?'M200 390 V500':'M200 390 Q200 440 390 550'} fill="none" stroke={C.cyan} strokeWidth={9}/><path d={copied?'M800 390 V730':'M800 390 Q800 440 610 550'} fill="none" stroke={C.pink} strokeWidth={9}/>{copied?<>{row(65,520,'[1, 2]',C.cyan)}{row(560,735,u<.5?'[1, 2]':'[1, 2, 3]',C.pink)}</>:row(310,550,s===2&&u>.3?'[1, 2, 3]':'[1, 2]',C.blue)}<T y={1000} size={45} color={C.yellow}>{copied?(u<.5?'RESET: b = a.copy()':'b.append(3)'):s===2?'b.append(3)':'b = a'}</T></g>;
}
function SkillScene({s,u}:any){
 const code=['a = [1, 2]','b = a.copy()','b.append(3)','print(a, b)'];
 return <g><rect x={35} y={130} width={930} height={680} rx={25} fill="#111d2d" stroke="#324258" strokeWidth={3}/>{[C.pink,C.yellow,C.cyan].map((c,i)=><Dot key={i} x={80+i*35} y={170} r={9} color={c}/>)}<T x={500} y={180} size={24} color={C.muted}>PYTHON · EXECUTED EXAMPLE</T>{code.map((line,i)=><g key={i} opacity={s===0?1:(s===1&&i>1)?.18:1}><rect x={60} y={240+i*110} width={880} height={87} rx={10} fill={(s===1?Math.floor(u*2):s===2?2+Math.floor(u*2):3)===i?'#223c47':'transparent'}/><T x={95} y={300+i*110} anchor="start" color={C.muted} size={27}>{i+1}</T><T x={155} y={300+i*110} anchor="start" size={46} color={i===1?C.cyan:C.ink}>{line}</T></g>)}{(s===0||s>=2)&&<><T x={90} y={895} anchor="start" size={37} color={C.muted}>OUTPUT</T><T x={90} y={970} anchor="start" size={57} color={C.cyan}>[1, 2]   [1, 2, 3]</T></>}</g>;
}
function Pendulum({t,s,u}:any){
 const l1=130,l2=s===0?130:520;
 return <g><T y={75} size={31} color={C.muted}>IDEAL SMALL-ANGLE MODEL · SAME GRAVITY</T>{[[270,l1,4,C.cyan],[730,l2,s===0?4:8,C.pink]].map(([x,l,period,color]:any,i:number)=>{const a=.24*Math.cos(t*2*Math.PI/period),bx=x+l*Math.sin(a),by=200+l*Math.cos(a);return <g key={i}><Line x1={x-100} y1={200} x2={x+100} y2={200} color={C.muted} width={12}/><Line x1={x} y1={200} x2={bx} y2={by} color={C.ink} width={6}/><Dot x={bx} y={by} r={40} color={color}/><T x={x} y={135} size={55} color={color}>{i===0?'L':s===0?'L':'4L'}</T><T x={x} y={850} size={43} color={color}>{i===0?'PERIOD T':s===0?'PERIOD T':'PERIOD 2T'}</T></g>})}<T y={990} size={53}>T ∝ √L</T></g>;
}
function Timeline({s,u}:any){
 const h=s===0?0:s===1?Math.min(2,Math.floor(u*3)):s===2?4:6;
 const n=2**h;
 return <g><T y={110} size={70} color={C.yellow}>{h} {h===1?'HOUR':'HOURS'}</T><T y={240} size={110}>{n}</T>{Array.from({length:n},(_,i)=>{const cols=n<=4?n:8,rows=Math.ceil(n/cols),r=n<=4?50:30;return <g key={i} transform={`translate(${500+(i%cols-(cols-1)/2)*(n<=4?150:103)},${600+(Math.floor(i/cols)-(rows-1)/2)*83})`}><ellipse rx={r} ry={r*.7} fill={i%2?C.cyan:C.blue}/><circle cx={-r*.3} cy={-r*.15} r={3} fill={C.dark}/><circle cx={r*.3} cy={-r*.15} r={3} fill={C.dark}/></g>;})}<T y={1000} size={41} color={C.muted}>{s===2?'AT SIX HOURS: ?':'N(t) = 2ᵗ · IDEAL DOUBLING'}</T></g>;
}
function Character({s,u,t}:any){
 const p=clamp(u);
 return <g>{s<=1?<><path d="M60 730 C200 730 200 90 470 140 S700 730 940 730" fill="none" stroke={C.pink} strokeWidth={13}/>{s===1&&<path d="M60 730 C250 730 270 500 470 500 S700 730 940 730" fill="none" stroke={C.cyan} strokeWidth={13}/>}<Face x={s===0?170:400+u*120} y={s===0?600:450} size={55} color={C.yellow} sad={s===0}/><T y={900} size={44} color={C.pink}>HIGH ACTIVATION BARRIER</T>{s===1&&<T y={980} size={44} color={C.cyan}>LOWER ALTERNATIVE PATH</T>}</>:<><Face x={500} y={540} size={170} name="ENZO" color={C.cyan} talk={Math.sin(t*8)>.4}/><path d="M430 400 Q500 470 570 400" fill="none" stroke={C.dark} strokeWidth={35}/>{s===2?<>{p<.45&&<Cube x={mix(100,450,ease(p/.3))} y={mix(190,330,ease(p/.3))} size={65} color={C.yellow}/>}{p>=.45&&<><Dot x={mix(520,850,(p-.45)/.55)} y={mix(350,180,(p-.45)/.55)} color={C.pink} r={30}/><Dot x={mix(560,900,(p-.45)/.55)} y={mix(370,360,(p-.45)/.55)} color={C.yellow} r={30}/></>}</>:<><Dot x={850} y={180} r={30} color={C.pink}/><Dot x={900} y={360} r={30} color={C.yellow}/><path d="M730 580 A260 260 0 1 0 460 810" fill="none" stroke={C.yellow} strokeWidth={8} strokeDasharray="20 16"/></>}<T y={955} size={45}>{s===2?'BIND → REACT → RELEASE':'CATALYST: NOT USED UP'}</T></>}</g>;
}
function Series({s,u,t}:any){
 const suitcase=(x:number,y:number,color:string,vals:string)=> <g><rect x={x+100} y={y-35} width={100} height={45} rx={13} fill="none" stroke={color} strokeWidth={9}/><rect x={x} y={y} width={300} height={200} rx={28} fill={color} fillOpacity={.17} stroke={color} strokeWidth={7}/><T x={x+150} y={y+115} size={47}>{vals}</T></g>;
 return <g><Face x={230} y={185} color={C.cyan} name="BYTE" talk={Math.sin(t*3)>0}/><Face x={760} y={185} color={C.pink} name="LOOP" talk={Math.sin(t*3)<0}/><T y={410} size={37} color={C.yellow}>{s===0?'“I MADE A CLONE.”':s===1?'“TWO TAGS. ONE SUITCASE.”':s===2?'“WHY DID BOTH CHANGE?”':'“FINALLY. TWO SUITCASES.”'}</T>{s===0?<T y={740} size={150} color={C.yellow}>?</T>:s<3?<>{suitcase(350,610,C.blue,s===2&&u>.3?'1, 2, 3':'1, 2')}<T x={330} y={590} color={C.cyan} size={45}>a ↘</T><T x={700} y={590} color={C.pink} size={45}>↙ b</T></>:<><T x={250} y={560} size={40} color={C.cyan}>a</T><T x={750} y={560} size={40} color={C.pink}>b</T>{suitcase(100,610,C.cyan,'1, 2')}{suitcase(600,610,C.pink,u<.5?'1, 2':'1, 2, 3')}</>}<T y={980} size={49} color={C.ink}>{s===2?'b.append(3)':s<3?'b = a':u<.5?'RESET: b = a.copy()':'b.append(3)'}</T></g>;
}
function Debate({s,u}:any){return <g>{s===0?<><T y={250} size={87}>6 ÷ 2(1 + 2)</T><T x={260} y={650} size={180} color={C.pink}>1</T><T x={740} y={650} size={180} color={C.cyan}>9</T><T y={610} size={50} color={C.muted}>or</T></>:s===1?<><T y={200} size={64}>(6 ÷ 2) × (1 + 2)</T><T y={420} size={90} color={C.blue}>3 × 3</T><T y={730} size={200} color={C.cyan}>= 9</T></>:s===2?<><T y={235} size={120}>6</T><Line x1={160} y1={295} x2={840} y2={295} color={C.ink}/><T y={405} size={77}>2 × (1 + 2)</T><T y={730} size={180} color={C.pink}>= 1</T></>:<><T y={250} size={60} color={C.cyan}>(6 ÷ 2) × 3 = 9</T><T y={560} size={60} color={C.pink}>6 ÷ (2 × 3) = 1</T><T y={850} size={55}>PARENTHESES ARE INFORMATION</T></>}</g>;}
function Pov({s,u}:any){
 const showCoins=s>=2;
 return <g><path d="M120 120 H880 L1000 990 H0Z" fill="#60402c" stroke="#ab8051" strokeWidth={6}/>{Array.from({length:6},(_,i)=><Line key={i} x1={120+i*150} y1={120} x2={i*200} y2={990} color="#7b5436" width={5}/>)}{[220,500,780].map((x,i)=><g key={i}>{!showCoins?<><path d={`M${x-65} 370 Q${x-140} 560 ${x-100} 650 Q${x} 720 ${x+100} 650 Q${x+140} 560 ${x+65} 370 Z`} fill="#c9aa75" stroke="#8e6d3e" strokeWidth={5}/><Line x1={x-65} y1={385} x2={x+65} y2={385} color="#5c3d25" width={12}/><T x={x} y={580} size={85} color="#624125">4</T></>:Array.from({length:4},(_,j)=><g key={j} opacity={s===2?ease((u-(i*4+j)*.025)/.25):1} transform={`translate(0 ${s===2?-100*(1-ease((u-(i*4+j)*.025)/.25)):0})`}><ellipse cx={x+(j%2-.5)*88} cy={440+Math.floor(j/2)*115} rx={35} ry={27} fill={C.yellow} stroke="#b78e33" strokeWidth={6}/><T x={x+(j%2-.5)*88} y={451+Math.floor(j/2)*115} size={26} color="#79541e">1</T></g>)}</g>)}<path d="M-30 1050 Q50 780 170 815 Q230 860 150 980" fill="#bb866b"/><path d="M1030 1050 Q950 780 830 815 Q770 860 850 980" fill="#bb866b"/><T y={220} size={s===3?75:45} color={C.yellow}>{s===3?'3 × 4 = 12':s===2?'4 + 4 + 4':'THREE EQUAL GROUPS'}</T><T y={760} size={29} color="#ead4b1">FICTIONAL SETTING · ILLUSTRATION</T></g>;
}

function Scene({id,s,u,t}:any){
 const p={s,u,t};
 switch(id){
  case 'curiosity':return <Waves {...p}/>;
  case 'what-if':return <Puck {...p}/>;
  case 'map':return <MapScene {...p}/>;
  case 'math':return <MathScene {...p}/>;
  case 'technology':return <Gravity {...p}/>;
  case 'money':return <Money {...p}/>;
  case 'myth':return <Balls {...p}/>;
  case 'inside':return <Circuit {...p}/>;
  case 'history':return <Search {...p}/>;
  case 'versus':return <Search {...p} versus/>;
  case 'predict':return <Balls {...p} predict/>;
  case 'conversation':return <Lists {...p} conversation/>;
  case 'skill':return <SkillScene {...p}/>;
  case 'variable':return <Pendulum {...p}/>;
  case 'timeline':return <Timeline {...p}/>;
  case 'character':return <Character {...p}/>;
  case 'series':return <Series {...p}/>;
  case 'debate':return <Debate {...p}/>;
  case 'pov':return <Pov {...p}/>;
  default:throw new Error('Unknown audition scene');
 }
}
const colors:any={pov:'#281e19',map:'#071b1b',math:'#070b14',character:'#11252a',series:'#18132b',money:'#0c2026'};
function Film({lesson}:any){
 const frame=useCurrentFrame(),t=frame/30;
 const found=lesson.segments.findIndex((v:any)=>t>=v.start&&t<v.end),s=found<0?3:found;
 const seg=lesson.segments[s],u=clamp((t-seg.start)/(seg.end-seg.start));
 const cap=lesson.captions.find((v:any)=>t>=v.start&&t<v.end+.06);
 const label=lesson.labels[s];
 return <AbsoluteFill style={{background:colors[lesson.id]||'#0b1425',color:C.ink,fontFamily:'DejaVu Sans,sans-serif'}}>
   <div style={{position:'absolute',top:150,left:90,right:140,height:165,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',fontWeight:800,fontSize:label.length>37?39:label.length>27?47:60,lineHeight:1.15,letterSpacing:-1.5}}>{label}</div>
   <svg width={900} height={945} viewBox="0 0 1000 1050" style={{position:'absolute',top:360,left:70}}><Scene id={lesson.id} s={s} u={u} t={t}/></svg>
   <PopCaptions caption={cap} now={t} top={1390}/>
   {lesson.segments.map((v:any,i:number)=><Sequence key={i} from={Math.round(v.start*30)} durationInFrames={Math.ceil(v.duration*30)}><Audio src={staticFile(`${lesson.id}/assets/${v.audio}`)}/></Sequence>)}
 </AbsoluteFill>;
}
const Root=()=> <Composition id="Audition" component={Film} width={1080} height={1920} fps={30} durationInFrames={900} calculateMetadata={({props}:any)=>({durationInFrames:props.lesson.frames})}/>;
registerRoot(Root);
