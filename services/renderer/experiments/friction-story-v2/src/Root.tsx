import React from 'react';
import {PopCaptions} from './PopCaptions';
import {AbsoluteFill,Audio,Composition,Sequence,registerRoot,staticFile,useCurrentFrame} from 'remotion';
const C={ink:'#243445',skin:'#d49a75',skinLight:'#efc5a2',orange:'#d66f42',blue:'#385b87',green:'#319f8c',red:'#d85149',paper:'#fff7e6'};
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const ease=(x:number)=>{const u=clamp(x);return u*u*(3-2*u)};
const lerp=(a:number,b:number,u:number)=>a+(b-a)*u;
const Line=({x1,y1,x2,y2,c=C.ink,w=4,...p}:any)=><line {...{x1,y1,x2,y2}} stroke={c} strokeWidth={w} strokeLinecap="round" {...p}/>;
const Text=({x,y,children,size=40,c=C.ink}:any)=><text {...{x,y}} textAnchor="middle" fontFamily="DejaVu Sans,sans-serif" fontSize={size} fontWeight={750} fill={c}>{children}</text>;
const Arrow=({x,y,dx,dy,c=C.green,label='',size=28}:any)=>{const a=Math.atan2(dy,dx),l=Math.min(18,Math.hypot(dx,dy)*.35);return <g><Line x1={x} y1={y} x2={x+dx} y2={y+dy} c={c} w={7}/><path d={`M${x+dx-l*Math.cos(a-.5)} ${y+dy-l*Math.sin(a-.5)}L${x+dx} ${y+dy}L${x+dx-l*Math.cos(a+.5)} ${y+dy-l*Math.sin(a+.5)}`} fill="none" stroke={c} strokeWidth={7} strokeLinecap="round"/>{label&&<Text x={x+dx*.5+dy*.15} y={y+dy*.5-24} c={c} size={size}>{label}</Text>}</g>};

function Defs(){return <defs>
 <linearGradient id="sky" x2="0" y2="1"><stop stopColor="#9bc9db"/><stop offset="1" stopColor="#eef1dc"/></linearGradient>
 <linearGradient id="redCar" x2="0" y2="1"><stop stopColor="#f28b69"/><stop offset=".5" stopColor="#d95446"/><stop offset="1" stopColor="#a3363c"/></linearGradient>
 <linearGradient id="blueCar" x2="0" y2="1"><stop stopColor="#82b4cb"/><stop offset=".5" stopColor="#50819b"/><stop offset="1" stopColor="#355e79"/></linearGradient>
 <linearGradient id="glass" x2=".8" y2="1"><stop stopColor="#c9eced"/><stop offset="1" stopColor="#77a8ba"/></linearGradient>
 <linearGradient id="floor" x2="0" y2="1"><stop stopColor="#e2d2af"/><stop offset="1" stopColor="#bfa381"/></linearGradient>
 <linearGradient id="phone" x2="1" y2="1"><stop stopColor="#88bfcd"/><stop offset=".5" stopColor="#b7bad5"/><stop offset="1" stopColor="#e2a99b"/></linearGradient>
 <radialGradient id="vignette"><stop offset=".65" stopColor="#203243" stopOpacity="0"/><stop offset="1" stopColor="#203243" stopOpacity=".12"/></radialGradient>
 </defs>}

function Tree({x,y,s=1}:any){return <g transform={`translate(${x} ${y}) scale(${s})`}><path d="M-10 0L-16-190H14L9 0" fill="#88684e"/><path d="M0-95L-62-150M0-125L54-187" fill="none" stroke="#88684e" strokeWidth={14}/><ellipse cx={-43} cy={-209} rx={82} ry={88} fill="#65927b"/><ellipse cx={38} cy={-234} rx={84} ry={104} fill="#77a58b"/><ellipse cx={3} cy={-285} rx={58} ry={71} fill="#8eb793"/><path d="M-58-230Q-15-267 19-238M13-294q24-22 41-2" fill="none" stroke="#bad1a6" strokeWidth={6} opacity={.6}/></g>}
function Street({scroll=0}:any){return <g>
 <rect width={720} height={1280} fill="url(#sky)"/><circle cx={595} cy={160} r={89} fill="#ffedb8"/>
 <g fill="#faf7e7" opacity={.85}><ellipse cx={160} cy={210} rx={135} ry={25}/><ellipse cx={124} cy={188} rx={51} ry={39}/><ellipse cx={205} cy={200} rx={55} ry={29}/></g>
 <path d="M0 470Q130 340 300 452T720 410V680H0Z" fill="#b5c7ad"/>
 <g transform={`translate(${-scroll} 0)`}>
 {[-1,0,1,2].map(i=><g key={i} transform={`translate(${i*380+85} 0)`}>
  <rect x={0} y={440} width={265} height={250} rx={3} fill={i%2?'#e6c8a6':'#dedac7'}/>
  <path d="M-24 445L125 330 290 445Z" fill="#6b7881"/><path d="M-10 447L125 344 277 447" fill="none" stroke="#91a0a2" strokeWidth={9}/>
  <rect x={20} y={483} width={76} height={90} rx={4} fill="url(#glass)" stroke="#f6ead7" strokeWidth={12}/><path d="M58 483v90M22 527h75" stroke="#f6ead7" strokeWidth={7}/>
  <rect x={172} y={485} width={65} height={86} rx={4} fill="url(#glass)" stroke="#f6ead7" strokeWidth={10}/><path d="M204 485v86M172 527h65" stroke="#f6ead7" strokeWidth={6}/>
  <path d="M112 690V549q36-25 56 0v141" fill="#7f9d9a"/><circle cx={153} cy={625} r={5} fill="#dac294"/>
  <path d="M-30 685q0-70 45-63q22-45 54-9q28-18 46 30v42" fill="#719a77"/><path d="M180 685q-3-66 36-57q21-38 50-2q30-2 42 59" fill="#7fa282"/>
 </g>)}
 <Tree x={70} y={698} s={1.16}/><Tree x={700} y={698} s={1.45}/>
 </g>
 <rect y={690} width={720} height={215} fill="#d9c9ae"/><path d="M0 717H720M0 889H720" stroke="#c0ac8b" strokeWidth={4}/>
 {Array.from({length:7},(_,i)=><Line key={i} x1={i*150-60-scroll%150} y1={717} x2={i*150-95-scroll%150} y2={889} c="#c3b093" w={3}/>)}
 <path d="M0 906H720V1280H0" fill="#6d7b83"/><path d="M0 905H720" stroke="#b6b5a9" strokeWidth={20}/>
 {[-1,0,1,2,3,4].map(i=><path key={i} d={`M${i*220-scroll%220} 1080h110`} stroke="#e7e2c9" strokeWidth={8} opacity={.65}/>)}
 </g>}

function Wheel({x,y,a=0}:any){return <g transform={`translate(${x} ${y}) rotate(${a})`}><circle r={43} fill="#24323e"/><circle r={29} fill="#b4c0c5" stroke="#748a97" strokeWidth={3}/>{[0,72,144,216,288].map(k=><path key={k} d="M-6-22H6L3-7H-3Z" transform={`rotate(${k})`} fill="#526674"/>)}<circle r={9} fill="#dce1db"/></g>}
function Car({x=360,y=900,color='red',s=1,t=0,locked=false,hit=0}:any){return <g transform={`translate(${x} ${y}) scale(${s})`}>
 <ellipse cy={15} rx={172} ry={20} fill="#283b46" opacity={.22}/>
 <g transform={`rotate(${Math.sin(hit*Math.PI*3)*2}) translate(0 ${-Math.sin(hit*Math.PI)*7})`} stroke={C.ink} strokeWidth={3.5} strokeLinejoin="round">
  <path d="M-163-65L-144-138Q-130-156-100-158H30Q67-157 100-103L151-92Q175-87 173-57L160-18H-150Q-178-23-163-65Z" fill={`url(#${color}Car)`}/>
  <path d="M-123-140H-44V-103H-139ZM-33-140H29Q55-140 80-103H-33Z" fill="url(#glass)"/>
  <path d="M-113-136L-125-108M-20-136L-30-108M8-136L-3-108" stroke="white" opacity={.25} strokeWidth={10}/>
  <path d="M-42-98V-30M-32-85H-11M-157-61H165" stroke="#293c4a" opacity={.6} fill="none" strokeWidth={3}/>
  <path d="M-160-83H-143V-65H-163Z" fill="#d13d3d"/><path d="M144-84H169V-66H142Z" fill="#f9efcf"/>
  <path d="M-171-30H-142M139-30H175" stroke="#b8c5c6" strokeWidth={10}/>
  {hit>.03&&<path d="M137-89L153-103 168-83 150-74 172-58" fill="none" stroke="#603b3a" strokeWidth={4}/>}
  <Wheel x={-104} y={-12} a={locked?0:t*280}/><Wheel x={106} y={-12} a={locked?0:t*280}/>
  <ellipse cx={148} cy={-12} rx={13} ry={6} fill={C.ink} opacity={.1}/>
 </g></g>}

function Shoe({x=0,y=0,s=1,angle=0}:any){return <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${s})`} stroke={C.ink} strokeWidth={3} strokeLinejoin="round"><path d="M-30-27L-2-32 18-13Q46-14 52 3L50 11H-36V-3Z" fill="#f2ece0"/><path d="M-36 4H51V16H-36Z" fill="#334e63"/><path d="M0-23L-7-11M12-17L6-7M23-12L18-3" stroke="#99a8ae" strokeWidth={3}/></g>}
function Human({x=360,y=900,s=1,t=0,pose='walk',fall=0,male=false,talk=0}:any){
 const phase=t*7, slip=pose==='slip',hang=pose==='hang',walking=pose==='walk';
 const hair=male?'#33343a':'#4d382d',skin=male?'#d49a75':'#e8ba94';
 const h=hang?0:walking?Math.abs(Math.sin(phase))*5:0;
 const leg=(i:number)=>walking?Math.sin(phase+i*Math.PI)*42:slip?lerp(i?-55:65,i?10:90,fall):hang?(i?-42:32):i?25:-25;
 return <g transform={`translate(${x} ${y}) scale(${s})`}>
  <ellipse cx={-100*fall} cy={8} rx={66+fall*50} ry={13} fill={C.ink} opacity={.12}/>
  <g transform={`translate(0 ${fall*61-h}) rotate(${-fall*90} 0 -100)`} stroke={C.ink} strokeWidth={3.2} strokeLinejoin="round" strokeLinecap="round">
  {[0,1].map(i=><g key={i}>
   <path d={`M${i?20:-20}-143Q${(i?22:-22)+leg(i)*.4} -80 ${leg(i)} ${walking?-Math.max(0,Math.sin(phase+i*Math.PI))*18-10:-10}`} fill="none" stroke={i?'#2f486a':'#3b5b7c'} strokeWidth={29}/>
   <Shoe x={leg(i)+4} y={walking?-Math.max(0,Math.sin(phase+i*Math.PI))*18-4:-4} angle={slip?(i?-15:12):walking?Math.sin(phase+i*Math.PI)*8:0}/>
  </g>)}
  <path d={male?'M-55-263Q0-280 57-262L44-143H-43Z':'M-47-260Q0-277 48-257L54-145Q0-130-54-145Z'} fill={male?'#79929b':C.orange}/>
  <path d="M-21-267V-288H21V-266Q0-254-21-267Z" fill={skin}/>
  {[-1,1].map((side,i)=>{
   const hx=hang?(side<0?18:30):slip?(side<0?lerp(-110,-35,fall):110):side<0?-52-Math.sin(phase)*13:82;
   const hy=hang?(side<0?-382:-350):slip?-230+Math.sin(t*11+i)*15:side<0?-150:-185;
   return <g key={i}><path d={`M${side*43}-250Q${slip&&side<0?lerp(-65,-35,fall):side*65} ${hang?-315:-187} ${hx} ${hy}`} fill="none" stroke={male?'#79929b':C.orange} strokeWidth={23}/><ellipse cx={hx} cy={hy} rx={10} ry={13} fill={skin}/></g>
  })}
  <path d="M-32-307Q-43-357-17-374Q21-389 41-355L43-328 53-316 42-308Q41-278 5-280Q-24-283-32-307Z" fill={skin}/>
  <path d={male?'M-36-325Q-52-365-25-378Q9-399 36-372L43-344 25-351 13-369Q-5-347-30-347Z':'M-32-315Q-60-337-45-365Q-22-397 18-382Q53-369 43-340L24-353Q1-325-25-333L-25-311Z'} fill={hair} stroke={hair}/>
  {!male&&<><ellipse cx={-45} cy={-361} rx={23} ry={26} fill={hair}/><path d="M-38-343Q-73-318-45-278" fill="none" stroke={hair} strokeWidth={20}/></>}
  <ellipse cx={25} cy={-331} rx={5} ry={fall>.1||hang?8:5} fill={C.ink} stroke="none"/>
  <path d={fall>.1?'M17-347L34-353':'M17-343L33-345'} fill="none" strokeWidth={3}/>
  {talk>.1||fall>.2?<ellipse cx={30} cy={-302} rx={8} ry={5+talk*9+fall*6} fill="#844b45"/>:<path d="M26-302q7 3 12-1" fill="none" strokeWidth={2.5}/>}<path d="M-21-322q-10-11-14 1q-1 10 12 12" fill={skin} strokeWidth={2}/>
  <path d="M-34-226L-32-162M26-241L19-186" stroke={male?'#a6b9b5':'#e89a67'} strokeWidth={4} opacity={.7}/>
  </g></g>}

function Dog({x=520,y=900,t=0,slip=0,s=1}:any){return <g transform={`translate(${x} ${y}) scale(${s})`} stroke="#715641" strokeWidth={3} strokeLinejoin="round" strokeLinecap="round">
 <ellipse cy={8} rx={89} ry={13} fill={C.ink} opacity={.12}/>
 <path d={`M-67-79Q-124 ${-110+Math.sin(t*9)*20}-110-155`} fill="none" stroke="#b38b60" strokeWidth={19}/>
 {[0,1,2,3].map(i=><path key={i} d={`M${i<2?-45:48}-72Q${(i<2?-48:53)+(i%2?1:-1)*slip*25} -30 ${(i<2?-55:55)+(i%2?1:-1)*(slip*35+Math.sin(t*9+i*2)*10)} -4`} fill="none" stroke={i%2?'#d6b17c':'#b78e61'} strokeWidth={17}/>)}
 <path d={`M-69-99Q-18-131 62-95L72-55Q3-26-65-52Z`} fill="#d4ae77"/>
 <path d="M51-113Q53-163 92-156Q123-149 126-119L152-110Q156-87 127-82L79-82Z" fill="#e0bc88"/>
 <path d="M59-144Q30-148 43-97Q67-76 75-125Z" fill="#ad8058"/><ellipse cx={117} cy={-122} rx={4} ry={slip?7:5} fill={C.ink}/><ellipse cx={147} cy={-106} rx={9} ry={6} fill={C.ink}/><path d="M133-86l-3 12q-8 11-13 0v-11" fill="#d17f76"/><path d="M72-95L113-81" stroke={C.blue} strokeWidth={11}/>
 </g>}

function Room({gym=false}:any){return <g><rect width={720} height={1280} fill={gym?'#becbd0':'#e4ded1'}/>
 <path d="M0 0H720V170L0 390Z" fill="white" opacity={.16}/><rect x={68} y={192} width={260} height={330} rx={6} fill="#b9d6d8" stroke="#eee9dd" strokeWidth={14}/><path d="M195 197v318M75 355h246" stroke="#eee9dd" strokeWidth={12}/>
 <path d="M68 518l260-321v155L181 520Z" fill="white" opacity={.12}/>
 <rect y={963} width={720} height={317} fill={gym?'#647783':'url(#floor)'}/><path d="M0 960H720" stroke={gym?'#82969c':'#c0aa89'} strokeWidth={12}/>
 {gym?<><path d="M60 942V652H190V942M525 942V622H664V942" stroke="#657b87" strokeWidth={13} fill="none"/><path d="M36 711H211M508 694H685" stroke="#4d606e" strokeWidth={11}/>{[55,188,530,664].map((x,i)=><rect key={i} x={x-14} y={665+(i>1?-17:0)} width={28} height={95} rx={8} fill="#435766"/>)}<rect x={170} y={958} width={410} height={80} rx={28} fill="#89a5b0"/><path d="M170 1000H580" stroke="#658593" strokeWidth={5}/></>:<><Tree x={590} y={945} s={.8}/><path d="M543 887H641L627 964H559Z" fill="#b77d5a"/><path d="M0 1130H720M180 966L60 1280M460 966L510 1280" stroke="#bca380" strokeWidth={3}/></>}
 </g>}

function Phone({x,y,rot=0,s=1}:any){return <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s})`} stroke={C.ink} strokeWidth={6}>
 <rect x={-73} y={-135} width={146} height={270} rx={24} fill="#344653"/><rect x={-64} y={-123} width={128} height={246} rx={17} fill="url(#phone)" strokeWidth={2}/><rect x={-24} y={-116} width={48} height={11} rx={6} fill={C.ink} stroke="none"/>
 <circle cx={0} cy={-20} r={37} fill="#eee5d9" opacity={.6} stroke="none"/>{[-1,0,1].map((i)=><rect key={i} x={i*35-10} y={70} width={20} height={20} rx={7} fill="#eee9dd" stroke="none"/>)}</g>}
function TopCar({x,y,angle=0,s=.65}:any){return <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${s})`} stroke={C.ink} strokeWidth={4}>
 <rect x={-60} y={-100} width={120} height={200} rx={28} fill="url(#redCar)"/>
 <path d="M-46-41Q0-59 46-41L43 50Q0 60-43 50Z" fill="url(#glass)"/><path d="M-43 11H43" stroke="#e78168" strokeWidth={15}/><path d="M-44-84H-17M17-84H44" stroke="#f8ecca" strokeWidth={10}/>
 {[-1,1].map(i=><g key={i}><rect x={i*61-9} y={-60} width={18} height={43} rx={5} fill={C.ink}/><rect x={i*61-9} y={37} width={18} height={43} rx={5} fill={C.ink}/></g>)}</g>}
function Track(){return <g><rect width={720} height={1280} fill="#dce5cf"/><path d="M20 180q150 50 160-130M550 60q-130 100 160 190" stroke="#bfd2b8" strokeWidth={90} fill="none"/><circle cx={360} cy={635} r={220} fill="none" stroke="#81908f" strokeWidth={145}/><circle cx={360} cy={635} r={220} fill="none" stroke="#f2edda" strokeWidth={4} strokeDasharray="21 20"/><circle cx={360} cy={635} r={6} fill={C.ink}/><path d="M45 1150l100-30M540 1060l100 35M70 530l40-30" stroke="#a9c2a4" strokeWidth={10} strokeLinecap="round"/></g>}

function Scene({name,t,u,duration,amp}:any){
 if(name==='hook'||name==='cars'){
  const impact=1.5,after=Math.max(0,t-impact),x=name==='hook'?30+t*35:t<impact?115+t*100:265+after*50;
  const other=name==='hook'?610:t<impact?610:610+after*50;
  const cam=name==='cars'?Math.max(0,x-290)*.55:0,hit=name==='cars'?clamp(after*2.8):0;
  return <><Street scroll={cam}/><g transform="translate(0 -40)"><path d="M643 900V570" stroke="#46555d" strokeWidth={12}/><rect x={616} y={500} width={54} height={131} rx={18} fill="#37464e"/><circle cx={643} cy={527} r={16} fill="#d95a50"/><circle cx={643} cy={566} r={14} fill="#6b685b"/><circle cx={643} cy={603} r={14} fill="#536f65"/></g>
  <Car x={other-cam} y={918} color="blue" locked/><Car x={x-cam} y={918} t={t} locked={name==='cars'&&t>.35} hit={hit}/>
  {name==='cars'&&after>0&&after<.8&&Array.from({length:7},(_,i)=><circle key={i} cx={435-cam+Math.cos(i)*after*75} cy={835+Math.sin(i)*after*60} r={10+after*18} fill="#f4e9d8" opacity={1-after/.8}/>)}
  </>
 }
 if(name==='dog'||name==='end'){
  const slip=name==='dog',fall=slip?ease((u-.18)/.37):0,drift=slip?t*22:t*14;
  const hx=245+drift,hy=900; const angle=-fall*90*Math.PI/180;
  const handLocalX=slip&&u>.18?110:82,handLocalY=slip&&u>.18?-230+Math.sin(t*11+1)*15:-185;
  const handX=hx+handLocalX*Math.cos(angle)-(handLocalY+100)*Math.sin(angle),handY=hy+fall*61-100+handLocalX*Math.sin(angle)+(handLocalY+100)*Math.cos(angle);
  return <><Street scroll={drift*.6}/><path d={`M${handX} ${handY}Q${400+drift} ${850+fall*40} ${565+drift} 844`} fill="none" stroke="#9b6d4d" strokeWidth={4}/><Dog x={490+drift} y={915} t={t} slip={fall} s={.8}/><Human x={hx} y={hy} t={t} pose={slip&&u>.18?'slip':'walk'} fall={fall}/></>
 }
 if(name==='phone'){
  const drop=clamp((t-.6)/1.0),rot=drop*6+(drop>=1?61*ease((t-1.6)*3):0),half=73*Math.abs(Math.sin(rot*Math.PI/180))+135*Math.abs(Math.cos(rot*Math.PI/180)),y=560+(963-half-560)*drop*drop;
  return <><Room/><path d="M720 1000L567 801Q514 731 450 701L442 592Q447 555 421 538L401 543 399 620 371 560Q356 530 336 545L357 633 327 590Q310 573 301 594L333 672Q366 740 439 764L527 938Z" fill={C.skinLight} stroke="#ae8067" strokeWidth={4}/>
   <Phone x={347+drop*22} y={y-(drop>=1?Math.sin(clamp((t-1.6)*4)*Math.PI)*15:0)} rot={rot}/>
   <path d="M443 608Q465 573 449 543Q434 523 416 537L401 577M402 626L377 592" fill="none" stroke={C.skinLight} strokeWidth={24} strokeLinecap="round"/><path d="M424 545l-6 22" stroke="#d3a482" strokeWidth={3} strokeLinecap="round"/>
  </>
 }
 if(name==='gym'||name==='drop'){
  const f=name==='drop'?clamp(t/.82):0,landing=f>=1?Math.sin(clamp((t-.82)*3)*Math.PI)*12:0;
  return <><Room gym/><path d="M430-20V1050" stroke="#a08562" strokeWidth={13}/><path d="M426 0V1050" stroke="#c5ab83" strokeWidth={3} strokeDasharray="4 8"/>
   <Human x={405} y={name==='gym'?735:735+218*f*f-landing} s={.94} t={t} pose={f>=1?'stand':'hang'} male talk={name==='gym'?amp:0}/>
   {f>=1&&<ellipse cx={405} cy={968} rx={107} ry={12} fill="#536e7e" opacity={.2}/>}
  </>
 }
 if(name==='why'){
  const p=clamp(t/3),x=150+340*(2*p-p*p);
  return <><rect width={720} height={1280} fill="#ece6d5"/><path d="M0 800H720V1280H0" fill="url(#floor)"/><path d="M0 800H720" stroke="#b59e80" strokeWidth={8}/>
   <g transform={`translate(${x} 796)`}><rect x={-72} y={-150} width={145} height={150} rx={7} fill="#c58e60" stroke="#795a43" strokeWidth={4}/><path d="M-66-145L-40-166H94L72-145Z" fill="#e1b987"/><path d="M72-145L94-166V-22L72 0Z" fill="#a9744c"/><path d="M-26-148v46l26-15 25 15v-46" fill="#ebc895"/></g>
   {p<.95&&<><Arrow x={x-20} y={813} dx={-115} dy={0} c={C.red} label="F"/><Arrow x={x-30} y={567} dx={140*(1-p)} dy={0} c={C.blue} label="v"/></>}
  </>
 }
 if(name==='shoe'||name==='nogrip'){
  const off=name==='nogrip',dx=off?-130*u:0;
  return <><rect width={720} height={1280} fill="#e8e4d4"/><path d="M0 835H720V1280H0" fill="url(#floor)"/><path d="M0 835H720" stroke="#bda583" strokeWidth={6}/>
   <g transform={`translate(${330+dx} 791) scale(2.8)`}><path d="M-26-29V-157H2V-32" fill={C.blue} stroke={C.ink} strokeWidth={3}/><path d="M-24-154V-45" stroke="#6484a0" strokeWidth={4}/><Shoe/></g>
   {off?<><Text x={526} y={744} size={46}>F = 0</Text><Arrow x={300+dx} y={930} dx={-120} dy={0} c={C.blue} label="v"/></>:<>
    {u>.08&&<Arrow x={350} y={927} dx={-180} dy={0} c={C.red} label="F"/>}
    {u>.45&&<Arrow x={330} y={765} dx={180} dy={0} c={C.green} label="F"/>}
   </>}
  </>
 }
 if(name==='turn'||name==='force'){
  let a,x,y,angle,dx=0,dy=0,label='F';
  if(name==='turn'){
   const q=clamp(u/.48);a=lerp(-1.623076923,-.7,q);x=360+220*Math.cos(a);y=635+220*Math.sin(a);angle=a*180/Math.PI+180;
   if(u>.48){const d=(u-.48)/.52*220;x+=-Math.sin(a)*d;y+=Math.cos(a)*d;label='F = 0'}
   else{dx=-Math.cos(a)*105;dy=-Math.sin(a)*105}
  }else{
   const half=duration*.46,fast=t>half;a=-2.2+.55*Math.min(t,half)+1.1*Math.max(0,t-half);x=360+220*Math.cos(a);y=635+220*Math.sin(a);angle=a*180/Math.PI+180;const len=fast?176:44;dx=-Math.cos(a)*len;dy=-Math.sin(a)*len;label=fast?'4F':'F';
  }
  return <><Track/>{name==='force'&&<Text x={360} y={240} size={51}>F = mv²/r</Text>}<TopCar x={x} y={y} angle={angle}/>
   {dx||dy?<Arrow x={x} y={y} dx={dx} dy={dy} label={label} size={32}/>:<Text x={x-110} y={y-75} size={39}>F = 0</Text>}
   {name==='force'&&<Text x={x+85} y={y-45} c={C.blue} size={40}>{t>duration*.46?'2v':'v'}</Text>}
  </>
 }
 return <Street/>;
}

function Video({lesson}:any){
 const frame=useCurrentFrame(),now=frame/30;
 const s=lesson.segments.find((s:any)=>s.start<=now&&s.end>now)||lesson.segments.at(-1);
 const t=now-s.start,d=s.end-s.start,u=clamp(t/d),amp=clamp((s.envelope?.[Math.floor(t*30)]||0)*2);
 const c=lesson.captions.find((c:any)=>c.start<=now&&c.end>now);
 return <AbsoluteFill style={{background:'#eae5d8'}}>
  <svg width={720} height={1280} viewBox="0 0 720 1280"><Defs/><Scene name={s.scene} {...{t,u,amp}} duration={d}/><rect width={720} height={1280} fill="url(#vignette)"/></svg>
  <PopCaptions caption={c} now={now} top={1068}/>
  {[['cars',1.5,'impact'],['phone',1.6,'tap'],['drop',.82,'mat']].map(([scene,at,file],i)=>{const v=lesson.segments.find((v:any)=>v.scene===scene);return <Sequence key={'fx'+i} from={Math.round((v.start+Number(at))*30)}><Audio src={staticFile(`friction-straight/assets/${file}.wav`)} volume={.45}/></Sequence>})}
  {lesson.segments.map((v:any,i:number)=><Sequence key={i} from={Math.round(v.start*30)} durationInFrames={Math.ceil(v.duration*30)}><Audio src={staticFile(`friction-straight/assets/${v.audio}`)}/></Sequence>)}
 </AbsoluteFill>
}
const Root=()=> <Composition id="Story" component={Video} width={720} height={1280} fps={30} durationInFrames={1500} defaultProps={{lesson:{segments:[],captions:[]}}} calculateMetadata={({props}:any)=>({durationInFrames:props.lesson.frames})}/>;
registerRoot(Root);
