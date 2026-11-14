import {PopCaptions} from './PopCaptions';
import React from 'react';
import {AbsoluteFill, Audio, Composition, Sequence, registerRoot, staticFile, useCurrentFrame} from 'remotion';

const C={ink:'#203441',paper:'#fff7df',sky:'#b9e7f0',blue:'#3469eb',mint:'#2fcbb8',red:'#f57864',yellow:'#ffe480',purple:'#8d76bf'};
const clamp=(x:number)=>Math.min(1,Math.max(0,x));
const ease=(x:number)=>{const t=clamp(x);return t*t*(3-2*t);};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const T=({x=540,y,size=46,fill=C.ink,children,anchor='middle',...p}:any)=><text x={x} y={y} fill={fill} fontSize={Math.min(size,960/Math.max(1,String(children).length*.62))} fontWeight={850} fontFamily="DejaVu Sans, sans-serif" textAnchor={anchor} {...p}>{children}</text>;
const L=({x1,y1,x2,y2,color=C.ink,w=8,...p}:any)=><line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={w} strokeLinecap="round" {...p}/>;
const Arrow=({x1,y1,x2,y2,color=C.blue,w=12}:any)=>{const a=Math.atan2(y2-y1,x2-x1),l=27;return <g><L {...{x1,y1,x2,y2,color,w}}/><path d={`M${x2-l*Math.cos(a-.6)} ${y2-l*Math.sin(a-.6)} L${x2} ${y2} L${x2-l*Math.cos(a+.6)} ${y2-l*Math.sin(a+.6)}`} fill="none" stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round"/></g>};

function Sneaker({x=0,y=0,scale=1,rot=0,color=C.blue}:any){return <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${scale})`} stroke={C.ink} strokeWidth={6} strokeLinejoin="round">
 <path d="M-68-55 L-17-65 18-29 Q84-33 95-4 L94 10-75 10 Q-87-10-68-55Z" fill={color}/>
 <path d="M-80-8 Q-10 7 94-4 L94 17-76 17Z" fill={C.paper}/>
 <path d="M-53-48 L-24-49-10-32-58-29Z" fill="#a9d7ff" strokeWidth={4}/>
 {[0,1,2].map(i=><L key={i} x1={-10+i*16} y1={-37+i*4} x2={-25+i*16} y2={-19+i*3} color={C.paper} w={5}/>)}
 <path d="M-55 11V17M-30 11V17M-5 11V17M20 11V17M45 11V17M70 11V17" fill="none" strokeWidth={3}/>
 </g>}

function Shark({x=540,y=1310,scale=1,t=0,pose='walk',talk=0,rot=0}:any){
 const walking=pose==='walk',slip=pose==='slip',scared=slip||pose==='panic';
 const bob=walking?Math.abs(Math.sin(t*8))*13:Math.sin(t*3)*3;
 const leg=(i:number)=>walking?Math.sin(t*8+i*2.1)*30:slip?(i-1)*70+Math.sin(t*16+i*2.1)*25:0;
 const blink=Math.sin(t*1.7)>.994;
 return <g transform={`translate(${x} ${y}) scale(${scale})`}>
  <ellipse cx={0} cy={28} rx={slip?260:205} ry={25} fill={C.ink} opacity={.14}/>
  <g transform={`rotate(${rot}) translate(0 ${-bob})`} stroke={C.ink} strokeWidth={7} strokeLinejoin="round" strokeLinecap="round">
   <g transform={`rotate(${Math.sin(t*4)*5} -190 -260)`}><path d="M-195-325L-347-425-318-285-358-174-202-207Z" fill="#26a7ad"/></g>
   <path d="M-88-436L-155-582Q-41-549 41-445Z" fill="#219dab"/>
   {[0,1,2].map(i=><g key={i}><path d={`M${-135+i*135} -143 Q${-130+i*135+leg(i)*.4} -83 ${-140+i*140+leg(i)} -27`} fill="none" stroke="#29b6b0" strokeWidth={29}/><Sneaker x={-145+i*140+leg(i)} y={-15} rot={walking?Math.sin(t*8+i*2.1)*8:slip?(i-1)*-12:0} scale={.88}/></g>)}
   <path d="M-180-130C-245-180-260-330-185-415Q-115-465 0-460C150-475 245-370 245-270Q255-180 140-120Q-30-70-180-130Z" fill={C.mint}/>
   <path d="M-177-292Q-88-184 232-278Q251-174 140-120Q-28-72-180-130Q-214-190-177-292Z" fill="#e2f7dc" stroke="none"/>
   {[-137,-113,-89].map(v=><path key={v} d={`M${v} -318q-13 25 3 50`} fill="none" stroke="#238d94" strokeWidth={6}/>)}
   <ellipse cx={80} cy={-354} rx={39} ry={blink?3:scared?51:43} fill="white" strokeWidth={5}/>
   <ellipse cx={166} cy={-354} rx={35} ry={blink?3:scared?48:39} fill="white" strokeWidth={5}/>
   {!blink&&<><ellipse cx={93} cy={-350} rx={scared?8:12} ry={scared?11:18} fill={C.ink} stroke="none"/><ellipse cx={178} cy={-350} rx={scared?8:11} ry={scared?11:17} fill={C.ink} stroke="none"/><circle cx={98} cy={-359} r={4} fill="white" stroke="none"/><circle cx={183} cy={-359} r={4} fill="white" stroke="none"/></>}
   <path d={scared?'M48-415L105-421M142-420L195-409':'M42-405Q80-419 109-399M143-398Q173-411 201-396'} fill="none" strokeWidth={10}/>
   {talk>.02?<g><ellipse cx={155} cy={-256} rx={49} ry={18+talk*32} fill="#532e4d"/><path d="M116-269L128-245 139-271 152-249 165-273 177-249 190-272" fill={C.paper} strokeWidth={3}/><ellipse cx={157} cy={-239+talk*8} rx={23} ry={8+talk*6} fill="#ec8b98" stroke="none"/></g>:<path d={scared?'M122-253q34-23 65 0':'M110-267Q156-216 201-270'} fill="none" strokeWidth={7}/>}
   <circle cx={207} cy={-311} r={5} fill={C.ink} stroke="none"/>
   <g transform={`rotate(${slip?-50+Math.sin(t*13)*25:pose==='hug'?50:Math.sin(t*6)*9} -15 -231)`}><path d="M-15-231Q47-193 66-111Q5-115-49-188Z" fill="#22afa8"/></g>
   {scared&&<path d="M-157-406q-38 33-17 47q28 9 17-47Z" fill="#69b7f7" strokeWidth={4}/>}
  </g>
 </g>
}

function Cup({x=0,y=0,s=1,t=0,talk=0,scared=false}:any){return <g transform={`translate(${x} ${y}) scale(${s})`} stroke={C.ink} strokeWidth={6} strokeLinejoin="round">
 <path d="M-55 5Q-93 40-92 110H84Q79 45 48 5Z" fill={C.purple}/>
 <path d="M-70-139Q-84-162-67-187M-10-145Q-25-173-6-198M37-145Q25-169 42-190" stroke="#d4a77a" opacity={.7} fill="none" strokeWidth={5} transform={`translate(0 ${Math.sin(t*3)*5})`}/>
 <path d="M68-91Q130-103 125-55Q124-21 71-27" fill="none" stroke={C.ink} strokeWidth={26}/><path d="M68-91Q130-103 125-55Q124-21 71-27" fill="none" stroke={C.paper} strokeWidth={14}/>
 <path d="M-82-118H83L66 8Q0 34-65 8Z" fill={C.paper}/><ellipse cx={0} cy={-118} rx={83} ry={24} fill="#c79463"/>
 <ellipse cx={0} cy={-119} rx={67} ry={14} fill="#795238"/><path d={`M-37-121Q0 ${-147+Math.sin(t*8)*9} 43-119Q17-99-37-121`} fill="#edd6a5" stroke="none"/>
 <path d={scared?'M-57-86L-17-95M20-95L58-86':'M-55-85L-18-85M19-85L56-85'} fill="none" strokeWidth={7}/>
 <ellipse cx={-34} cy={-67} rx={8} ry={12} fill={C.ink}/><ellipse cx={36} cy={-67} rx={8} ry={12} fill={C.ink}/>
 {talk>.02?<ellipse cx={3} cy={-24} rx={21} ry={8+talk*17} fill="#532e4d"/>:<path d={scared?'M-15-20Q4-36 23-20':'M-17-26Q3-10 24-26'} fill="none"/>}
 <path d="M-68 65Q-11 86 72 54" fill="none" stroke={C.purple} strokeWidth={24}/>
 </g>}

function Wheel({x,y,rot=0,r=65}:any){return <g transform={`translate(${x} ${y}) rotate(${rot})`}><circle r={r} fill={C.ink}/><circle r={r*.62} fill={C.paper} stroke="#526775" strokeWidth={7}/>{[0,60,120].map(a=><line key={a} x1={-r*.44} x2={r*.44} y1={0} y2={0} stroke="#81949b" strokeWidth={9} transform={`rotate(${a})`}/>)}<circle r={12} fill={C.ink}/></g>}
function Car({x=540,y=1260,s=1,t=0,locked=false,talk=0,crash=0,steer=0}:any){return <g transform={`translate(${x} ${y}) scale(${s})`}>
 <ellipse cx={0} cy={50} rx={285} ry={24} fill={C.ink} opacity={.15}/>
 <g transform={`scale(${1-crash*.1} ${1+crash*.08})`}>
 <path d="M-267-93L-224-239Q-194-285-111-284H78Q142-272 190-166L273-131Q309-109 305-47L271-8H-242Q-298-28-267-93Z" fill={C.yellow} stroke={C.ink} strokeWidth={8} strokeLinejoin="round"/>
 <path d="M-202-239Q-172-262-111-260H-78V-164H-230ZM-53-260H65Q119-247 157-164H-53Z" fill="#91d7e5" stroke={C.ink} strokeWidth={6}/>
 <path d="M-32-251H61Q107-239 139-176H-32Z" fill="#c1edf0"/>
 <Cup x={36} y={-174} s={.54} {...{t,talk}} scared={locked}/>
 <path d="M-65-162V-28M-267-86H294M-33-135H4" stroke={C.ink} strokeWidth={6} fill="none"/>
 <rect x={250} y={-124} width={44} height={35} rx={9} fill={C.paper} stroke={C.ink} strokeWidth={5}/>
 <rect x={-280} y={-125} width={28} height={39} rx={8} fill={C.red}/>
 <path d="M-277-28H-222M247-28H306" stroke={C.ink} strokeWidth={17} strokeLinecap="round"/>
 <Wheel x={-166} y={-7} rot={locked?0:t*200}/><g transform={`translate(177 -7) scale(${1-Math.abs(steer)*.25} 1)`}><Wheel x={0} y={0} rot={locked?0:t*200}/></g>
 <T x={0} y={-66} size={26}>DECAF EXPRESS</T>
 </g></g>}

function City({t=0,off=false,scroll=0}:any){return <g>
 <rect width={1080} height={1920} fill={C.sky}/><circle cx={885} cy={297} r={126} fill={C.yellow}/>
 <g fill={C.paper} opacity={.8}>{[[120,400],[640,235],[935,535]].map(([x,y],i)=><g key={i} transform={`translate(${x-Math.sin(t*.1+i)*20} ${y})`}><ellipse rx={110} ry={31}/><ellipse cx={-30} cy={-22} rx={43} ry={40}/><ellipse cx={35} cy={-11} rx={45} ry={38}/></g>)}</g>
 <g opacity={.26} fill="#4c9cbb">{Array.from({length:10},(_,i)=><rect key={i} x={i*130-80} y={600-(i%3)*80} width={105} height={460+(i%3)*80} rx={8}/>)}</g>
 <g transform={`translate(${-((scroll%470)+470)%470} 0)`}>
  {Array.from({length:5},(_,i)=><g key={i} transform={`translate(${i*470-260} 0)`}>
   <path d="M0 1130V690L40 647H350L390 690V1130Z" fill={i%2?'#eab09a':'#b8b0d5'} stroke={C.ink} strokeWidth={6}/>
   <rect x={30} y={687} width={330} height={30} fill={C.paper} stroke={C.ink} strokeWidth={4}/>
   {[0,1,2].map(k=><g key={k}><rect x={35+k*108} y={755} width={76} height={115} rx={35} fill="#617a91" stroke={C.ink} strokeWidth={5}/><path d={`M${73+k*108} 758V868M${38+k*108} 813H${109+k*108}`} stroke={C.paper} strokeWidth={5}/></g>)}
   <rect x={25} y={910} width={339} height={215} fill="#557f89" stroke={C.ink} strokeWidth={5}/><rect x={160} y={943} width={84} height={182} fill="#b7d7d8" stroke={C.ink} strokeWidth={5}/>
   <path d="M10 908H380L365 960H25Z" fill={i%2?C.red:C.mint} stroke={C.ink} strokeWidth={5}/>
   {[0,1,2,3,4].map(k=><path key={k} d={`M${30+k*70} 911h31l-2 46h-34Z`} fill={C.paper}/>)}
   <rect x={46} y={898} width={300} height={42} rx={8} fill={C.paper} stroke={C.ink} strokeWidth={4}/><T x={196} y={928} size={25}>{i%2?'FOAM & CO.':'THE DAILY GRIND'}</T>
  </g>)}
 </g>
 <path d="M0 1120H1080V1300H0Z" fill="#e6d5b1"/><path d="M0 1120H1080M0 1270H1080" stroke={C.ink} strokeWidth={6}/>
 {Array.from({length:9},(_,i)=><L key={i} x1={i*170-scroll%170} y1={1120} x2={i*170-45-scroll%170} y2={1270} color="#bda982" w={4}/>)}
 <rect y={1300} width={1080} height={620} fill={off?'#83bfc9':'#697985'}/>
 <path d="M0 1300H1080" stroke={C.ink} strokeWidth={9}/>
 {Array.from({length:6},(_,i)=><path key={i} d={`M${i*280-scroll%280} 1400h125`} stroke={C.paper} strokeWidth={13} strokeLinecap="round" opacity={.6}/>)}
 {off&&[0,1,2,3].map(i=><path key={i} d={`M${80+i*280} 1340l110-25M${100+i*280} 1360l60-14`} stroke="#d6f8f3" strokeWidth={5} strokeLinecap="round" opacity={.8}/>)}
 </g>}

function Badge({on=true,large=false,pulse=0}:any){return <g transform={large?'translate(540 540) scale(1.65)':'translate(812 175)'}>
 <rect x={-147} y={-53} width={294} height={106} rx={28} fill={C.paper} stroke={C.ink} strokeWidth={6}/>
 <T x={-30} y={-12} size={21}>GROUND GRIP</T><T x={-30} y={23} size={25} fill={on?'#008c72':'#db554d'}>{on?'ON':'OFF'}</T>
 <rect x={74} y={-28} width={49} height={57} rx={24} fill={on?C.mint:C.red} stroke={C.ink} strokeWidth={4}/><circle cx={98} cy={on?-8:10} r={17} fill={C.paper} stroke={C.ink} strokeWidth={3}/>
 {pulse>0&&<rect x={-147-pulse*22} y={-53-pulse*14} width={294+pulse*44} height={106+pulse*28} rx={34} fill="none" stroke={on?C.mint:C.red} strokeWidth={7} opacity={1-pulse}/>}
 </g>}
function Foam({x=820,y=1290,t=0,hit=0}:any){return <g transform={`translate(${x} ${y})`}>
 {[[-65,-90,0],[55,-90,1],[-10,-198,2],[50,-302,3]].map(([dx,dy,i])=><g key={i} transform={`translate(${dx+hit*(i-1)*70} ${dy-Math.sin(clamp(hit)*Math.PI)*70}) rotate(${hit*(i%2?-1:1)*25})`}>
 <rect x={-63} y={-60} width={126} height={120} rx={18} fill={i%2?'#f7b7b0':'#f9edd0'} stroke={C.ink} strokeWidth={6}/><path d="M-42-39L-29-33M28 32L39 36M-28 35L-20 27" stroke="#c6a87d" strokeWidth={6} strokeLinecap="round"/><T x={0} y={8} size={22}>FOAM</T></g>)}
 </g>}
function Burst({x,y,text,scale=1}:any){return <g transform={`translate(${x} ${y}) scale(${scale})`}><path d="M-145-30L-180-110-74-76-42-147 9-82 85-122 91-55 176-61 129 4 184 64 82 61 56 125-4 72-90 107-83 40-171 31Z" fill={C.yellow} stroke={C.ink} strokeWidth={6}/><T x={0} y={15} size={47} transform="rotate(-8)">{text}</T></g>}
function SpeedLines({t=0}:any){return <g opacity={.65}>{Array.from({length:8},(_,i)=><L key={i} x1={(i*211-t*400)%1400} y1={600+(i%5)*130} x2={(i*211-t*400)%1400+100} y2={600+(i%5)*130} color={C.paper} w={7}/>)}</g>}

function TopCar({x,y,angle=0,scale=1}:any){return <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`} stroke={C.ink} strokeWidth={5}><rect x={-73} y={-96} width={146} height={192} rx={40} fill={C.yellow}/><rect x={-54} y={-43} width={108} height={94} rx={19} fill="#b8e8ed"/><rect x={-57} y={-82} width={33} height={14} rx={5} fill="white"/><rect x={24} y={-82} width={33} height={14} rx={5} fill="white"/>{[-1,1].map(j=><g key={j}><rect x={j*73-11} y={-55} width={22} height={43} rx={5} fill={C.ink}/><rect x={j*73-11} y={38} width={22} height={43} rx={5} fill={C.ink}/></g>)}</g>}

function Scene({scene,t,u,speaking,amp}:any){
 const off=['slip','reaction','car','crash','why'].includes(scene)||(scene==='switch'&&u>.72);
 const street=!['shoe','tire','restore'].includes(scene);
 const scroll=['slip','reaction'].includes(scene)?t*115:scene==='car'?t*160:scene==='hook'?t*22:0;
 return <>
 {street?<City t={t} off={off} scroll={scroll}/>:<><rect width={1080} height={1920} fill={C.paper}/><circle cx={1050} cy={-40} r={440} fill="#d6efdc"/><circle cx={40} cy={1910} r={470} fill="#ece0be"/></>}
 <T x={58} y={125} size={25} anchor="start">ZERO GRIP ZONE</T>
 {scene!=='switch'&&<Badge on={!off}/>}
 {scene==='hook'&&<>
  <T y={320} size={62}>What if</T><T y={408} size={105} fill={C.blue}>FRICTION</T><T y={490} size={72}>just quit?</T>
  <Car x={((t*100+800)%1600)-300} y={1160} s={.48} t={t}/>
  <Shark x={500+t*10} y={1300} scale={1.03} t={t}/>
 </>}
 {scene==='switch'&&<>
  <T y={340} size={56}>“I have THREE sneakers.”</T>
  <Badge on={u<.72} large pulse={u>.72?clamp((u-.72)*8):0}/>
  <T y={675} size={27}>SHOES + TIRES ONLY</T>
  <Shark x={520} y={1320} scale={.96} t={t} talk={amp} pose={u>.72?'panic':'stand'}/>
  {u>.72&&<Burst x={865} y={850} text="uh-oh" scale={.6}/>}
 </>}
 {scene==='slip'&&<>
  <T y={375} size={65}>ALL KICK. ZERO GRIP.</T>
  <SpeedLines t={t}/><Shark x={mix(370,650,u)} y={1290} scale={1.04} t={t} pose="slip" talk={amp} rot={-8+Math.sin(t*7)*4}/>
  <path d={`M${250+u*280} 1325h90M${120+u*280} 1340h65`} stroke={C.paper} strokeWidth={9} strokeLinecap="round"/>
 </>}
 {scene==='reaction'&&<>
  <T y={360} size={76}>SCREENSAVER MODE</T>
  <SpeedLines t={t}/><Shark x={540} y={1340} scale={1.26} t={t} pose="slip" talk={amp} rot={-4}/>
  <g transform={`translate(${830+Math.sin(t*4)*15} 590)`}><T x={0} y={0} size={76}>...</T></g>
 </>}
 {scene==='car'&&<>
  <T y={350} size={76}>BRAKES: PRESSED.</T><T y={432} size={60} fill="#bd413c">CAR: STILL GOING.</T>
  <Car x={470+u*140} y={1290} s={1.28} t={t} locked={t>.9} talk={amp}/>
  <g transform="translate(260 690)"><circle r={118} fill={C.paper} stroke={C.ink} strokeWidth={6}/><Wheel x={0} y={0} rot={t<.9?t*260:234} r={83}/><T x={0} y={162} size={31}>{t>.9?'LOCKED':'SPINNING'}</T>{t>.9&&<L x1={-60} y1={-60} x2={60} y2={60} color={C.red} w={12}/>}</g>
  <circle cx={797} cy={684} r={143} fill={C.paper} stroke={C.ink} strokeWidth={6}/><Cup x={797} y={724} s={.95} t={t} talk={amp} scared/><T x={797} y={884} size={30}>NOT IN THE MANUAL.</T>
 </>}
 {scene==='crash'&&<>
  <T y={350} size={70}>STEERING: ALSO NOPE.</T>
  <path d="M170 850Q420 850 510 570" fill="none" stroke={C.paper} strokeWidth={12} strokeDasharray="20 20"/>
  <T x={352} y={590} size={25}>WANTED TO TURN</T>
  <Foam x={905} y={1310} hit={clamp((u-.46)*2.5)}/>
  <Car x={u<.46?mix(170,570,u/.46):570-Math.sin(clamp((u-.46)*7)*Math.PI)*15} y={1310} s={.96} t={t} locked talk={amp} steer={1} crash={u>.46?Math.sin(clamp((u-.46)*5)*Math.PI):0}/>
  {u>.44&&u<.75&&<Burst x={780} y={825} text="POOF!" scale={.95}/>}</>}
 {scene==='why'&&<>
  <rect y={250} width={1080} height={1110} fill={C.paper} opacity={.9}/>
  <T y={363} size={72}>NO PUSH. STILL COASTING.</T>
  <Shark x={460} y={1150} scale={.68} t={t} pose="slip"/>
  <Arrow x1={565} y1={780} x2={565} y2={590} color="#159983"/><T x={570} y={542} size={35}>NORMAL FORCE</T>
  <Arrow x1={565} y1={920} x2={565} y2={1110} color={C.red}/><T x={685} y={1100} size={31}>GRAVITY</T>
  <Arrow x1={750} y1={885} x2={960} y2={885}/><T x={850} y={823} size={30}>VELOCITY</T>
  <T y={1260} size={43}>Fₓ = 0  →  aₓ = 0</T><T y={1330} size={25}>During the short slide, neglect air drag.</T>
 </>}
 {scene==='shoe'&&<>
  <T y={365} size={68}>HOW WALKING WORKS</T><T y={432} size={31}>GRIP RESTORED · CLOSE-UP</T>
  <rect x={55} y={1050} width={970} height={225} rx={20} fill="#dbcba4" stroke={C.ink} strokeWidth={6}/>
  <path d="M80 1050h920" stroke={C.ink} strokeWidth={9}/>
  <g transform={`translate(${540+Math.sin(t*2)*3} 1015) scale(3)`}><path d="M-43-60V-110H2V-44" fill={C.mint} stroke={C.ink} strokeWidth={5}/><Sneaker/></g>
  <Arrow x1={540} y1={1160} x2={225} y2={1160} color={C.red}/><T x={540} y={1230} size={34} fill="#a8463e">SHOE PUSHES GROUND BACK</T>
  <Arrow x1={430} y1={810} x2={745} y2={810} color="#159983"/><T y={620} size={34} fill="#087864">GROUND PUSHES SHOE FORWARD</T>
  <T y={1370} size={35}>Equal forces. Different objects.</T>
 </>}
 {['tire','restore'].includes(scene)&&(()=>{
  const a=-1.8+u*1.7, cx=500,cy=1000,r=280, carX=cx+r*Math.cos(a),carY=cy+r*Math.sin(a);
  return <>
   <T y={365} size={scene==='restore'?63:67}>{scene==='restore'?'THERE’S A GRIP LIMIT.':'TURNING NEEDS A FORCE.'}</T>
   <T y={432} size={31}>GRIP RESTORED · TOP VIEW</T>
   <circle cx={cx} cy={cy} r={r} fill="none" stroke="#aab5b3" strokeWidth={210}/><circle cx={cx} cy={cy} r={r} fill="none" stroke={C.paper} strokeWidth={5} strokeDasharray="27 23"/>
   <circle cx={cx} cy={cy} r={8} fill={C.ink}/><T x={cx} y={cy+55} size={27}>TURN CENTER</T>
   <TopCar x={carX} y={carY} angle={a*180/Math.PI+180} scale={.64}/>
   <Arrow x1={carX*.82+cx*.18} y1={carY*.82+cy*.18} x2={carX*.2+cx*.8} y2={carY*.2+cy*.8} color="#00876f" w={13}/>
   {scene==='tire'?<><T y={592} size={35} fill="#00876f">STATIC FRICTION POINTS INWARD</T><T y={1390} size={42}>No sideways force → no turn.</T></>:<>
    <T y={573} size={57}>mv²/r ≤ μₛN</T><T y={627} size={27}>TURNING DEMAND ≤ AVAILABLE GRIP</T>
    <rect x={173} y={1325} width={734} height={95} rx={25} fill={C.yellow} stroke={C.ink} strokeWidth={5}/>
    <T y={1387} size={43}>2× SPEED  →  4× FORCE</T><T y={1464} size={26}>SAME CAR · SAME TURN RADIUS</T>
   </>}
  </>})()}
 {scene==='payoff'&&<>
  <T y={340} size={79}>GRIP APPRECIATION DAY.</T>
  <Foam x={915} y={1290}/><Car x={840} y={1310} s={.45} t={0}/>
  <Shark x={430} y={1320} scale={1.07} t={t} pose="hug" talk={amp} rot={-10+ease(u)*10}/>
  <g transform={`translate(710 ${625-Math.sin(t*4)*12})`}><path d="M0 20C-80-30-50-90 0-50C50-90 80-30 0 20Z" fill={C.red} stroke={C.ink} strokeWidth={6}/></g>
 </>}
 </>
}

const Story=({lesson}:any)=>{
 const f=useCurrentFrame(),now=f/30;
 const seg=lesson.segments.find((s:any)=>s.start<=now&&s.end>now)||lesson.segments.at(-1);
 const t=Math.max(0,now-seg.start),u=clamp(t/(seg.end-seg.start));
 const active=now<seg.start+seg.duration;
 const amp=active?clamp((seg.envelope?.[Math.floor(t*30)]||0)*2.2):0;
 const caption=lesson.captions.find((c:any)=>c.start<=now&&c.end>now);
 const speaker=seg.speaker, color=speaker==='shark'?C.mint:speaker==='driver'?C.yellow:'#e1c8ff';
 const cues=[['switch',.72,'click'],['slip',.02,'slide'],['crash',.46,'boing'],['shoe',.02,'pop'],['payoff',.03,'grip']];
 return <AbsoluteFill style={{background:C.paper}}>
  <svg viewBox="0 0 1080 1920" width="1080" height="1920"><Scene scene={seg.scene} t={t} u={u} speaking={active} amp={speaker==='narrator'?0:amp}/>
   <path d="M0 1510Q540 1455 1080 1510V1920H0Z" fill={C.ink}/>
   <T x={540} y={1808} size={25} fill="#b2c4cb">A LITTLE CHAOS. ACTUAL PHYSICS.</T>
   <rect x={0} y={1898} width={1080*now/lesson.duration} height={10} fill={C.mint}/>
  </svg>
  <PopCaptions caption={caption} now={now} top={1517}/>
  <Audio src={staticFile('friction-story/assets/music.wav')} volume={.65}/>
  {lesson.segments.map((s:any,i:number)=><Sequence key={i} from={Math.round(s.start*30)} durationInFrames={Math.ceil(s.duration*30)}><Audio src={staticFile(`friction-story/assets/${s.audio}`)}/></Sequence>)}
  {cues.map(([name,when,file],i)=>{const s=lesson.segments.find((s:any)=>s.scene===name);return <Sequence key={i} from={Math.round((s.start+Number(when)*(s.end-s.start))*30)}><Audio src={staticFile(`friction-story/assets/${file}.wav`)} volume={.6}/></Sequence>})}
 </AbsoluteFill>
};
const Root=()=> <Composition id="Story" component={Story} width={1080} height={1920} fps={30} durationInFrames={1500} defaultProps={{lesson:{segments:[],captions:[]}}} calculateMetadata={({props}:any)=>({durationInFrames:props.lesson.frames})}/>;
registerRoot(Root);
