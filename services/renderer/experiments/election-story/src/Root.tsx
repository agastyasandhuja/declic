import React,{useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,Audio,Composition,Sequence,continueRender,delayRender,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import {PopCaptions} from './PopCaptions';
import {createWorld} from './World';
import {states,totals,ease,clamp} from './ElectionMath.mjs';
const O='#df8738',T='#208e88',ink='#243e4b';
const Text=({x,y,size=30,color=ink,children}:any)=><text x={x} y={y} textAnchor="middle" fontFamily="DejaVu Sans,sans-serif" fontSize={size} fontWeight="bold" fill={color}>{children}</text>;
const Card=({x=52,y=95,w=616,h=290,children}:any)=><g><rect x={x} y={y+9} width={w} height={h} rx={22} fill="#294657" opacity={.12}/><rect x={x} y={y} width={w} height={h} rx={22} fill="#fff9ec"/>{children}</g>;
function Score({electoral=false,u=1}:any){
 const val=electoral?totals.electoral:totals.popular,den=electoral?15:300,p=ease(u/.5);
 return <Card h={245}><Text x={360} y={148} size={24}>{electoral?'Electoral votes':'Popular votes'}</Text>
  {['orange','teal'].map((key,i)=><g key={key}><circle cx={97} cy={202+i*77} r={13} fill={i?T:O}/><rect x={125} y={184+i*77} width={438} height={37} rx={8} fill="#e5e8dd"/><rect x={125} y={184+i*77} width={438*val[key]/den*p} height={37} rx={8} fill={i?T:O}/><Text x={609} y={213+i*77} size={30} color={i?T:O}>{Math.round(val[key]*p)}</Text></g>)}
 </Card>;
}
function Diagram({scene:s,u}:any){
 if(['hook','popular','electoral','outro'].includes(s))return <Score electoral={s==='electoral'||s==='outro'} u={s==='hook'?1:u}/>;
 if(s==='majority')return <Card h={350}>
  <Text x={360} y={161} size={43}>270 / 538</Text>
  {Array.from({length:538},(_,i)=><rect key={i} x={88+i%28*19.7} y={190+Math.floor(i/28)*10} width={15} height={6} rx={2} fill={i<Math.round(270*ease(u/.55))?T:'#d9d9c9'}/>)}
 </Card>;
 if(s==='allocation')return <Card h={230}><Text x={360} y={160} size={34}>House seats + 2</Text><path d="M190 192H530" stroke="#d7d8c7" strokeWidth={2}/><Text x={360} y={260} size={38}>D.C. = 3</Text></Card>;
 if(s==='exceptions')return <Card h={320}>
  <Text x={360} y={150} size={28}>48 states + D.C.</Text><Text x={360} y={200} size={32}>Winner takes all</Text>
  <path d="M90 225H630" stroke="#d7d8c7" strokeWidth={2}/><Text x={360} y={270} size={27}>Maine · Nebraska</Text><Text x={360} y={315} size={23}>2 statewide + 1 per district</Text>
  {['ME','NE'].map((v,k)=><g key={v}><Text x={160+k*280} y={375} size={20}>{v}</Text>{Array.from({length:4+k},(_,i)=><rect key={i} x={191+k*280+i*26} y={354} width={21} height={25} rx={4} fill={i<2?O:T} opacity={ease((u-.25-i*.06)/.25)}/>)}</g>)}
 </Card>;
 if(['toy','narrow','landslide'].includes(s))return <Card y={80} h={275}>
  <Text x={360} y={125} size={22}>Fictional three-state example</Text>
  {states.map((v:any,i:number)=>{const reveal=s==='landslide'||s==='narrow'&&i<2;return <g key={v.id}>
   <Text x={164+i*196} y={173} size={30}>{v.id}</Text><Text x={164+i*196} y={216} size={22}>5 electors</Text>
   {reveal?<><Text x={164+i*196} y={265} size={27} color={T}>{v.teal}</Text><Text x={164+i*196} y={307} size={27} color={O}>{v.orange}</Text><circle cx={121+i*196} cy={255} r={7} fill={T}/><circle cx={121+i*196} cy={297} r={7} fill={O}/></>:<Text x={164+i*196} y={280} size={32}>?</Text>}
  </g>})}
 </Card>;
 if(s==='certify')return <Card h={310}>
  {u<.5?<><Text x={190} y={175} size={32}>December</Text><Text x={530} y={175} size={32}>January</Text><Text x={190} y={235} size={23}>Electors vote</Text><Text x={530} y={235} size={23}>Congress counts</Text><path d="M302 206H402l-14-12m14 12l-14 12" fill="none" stroke={T} strokeWidth={6}/><circle cx={302+100*ease(u/.5)} cy={206} r={10} fill={O}/></>:<><Text x={360} y={160} size={28}>No electoral majority?</Text><Text x={360} y={225} size={32}>House chooses president</Text><Text x={360} y={285} size={25}>1 vote / state delegation</Text><Text x={360} y={345} size={22}>From the top 3 candidates</Text></>}
 </Card>;
 return null;
}
const Movie=({lesson}:{lesson:any})=>{
 const frame=useCurrentFrame(),t=frame/30,canvas=useRef<HTMLCanvasElement>(null),world=useRef<any>(null);
 const [ready]=useState(()=>delayRender('Build reused voxel rig and new election world'));
 const beat=lesson.segments.find((b:any)=>t>=b.start&&t<b.end)||lesson.segments.at(-1),u=clamp((t-beat.start)/(beat.end-beat.start));
 useLayoutEffect(()=>{world.current=createWorld(canvas.current!);world.current.update(beat,u,t);continueRender(ready);return()=>world.current?.dispose()},[]);
 useLayoutEffect(()=>world.current?.update(beat,u,t),[frame]);
 return <AbsoluteFill style={{background:'#a9d5e4'}}>
  <canvas ref={canvas} width={720} height={1280} style={{width:720,height:1280}}/>
  <svg viewBox="0 0 720 1280" style={{position:'absolute',inset:0}}><Diagram scene={beat.scene} u={u}/></svg>
  <PopCaptions words={lesson.words} now={t} top={1030}/>
  {lesson.segments.map((s:any,i:number)=><Sequence key={i} from={Math.round(s.start*30)} durationInFrames={Math.ceil(s.duration*30)}><Audio src={staticFile(`${lesson.id}/assets/${s.audio}`)}/></Sequence>)}
  <Audio src={staticFile(`${lesson.id}/assets/ambience.wav`)} volume={.35}/>
 </AbsoluteFill>;
};
registerRoot(()=> <Composition id="VoxelStory" component={Movie} width={720} height={1280} fps={30} durationInFrames={1500} calculateMetadata={({props})=>({durationInFrames:props.lesson.frames})}/>);
