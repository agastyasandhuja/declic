import {MathLesson} from './MathLesson';
import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, OffthreadVideo, registerRoot, staticFile, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import CustomScene from './CustomScene';
import {ReferenceLesson} from './ReferenceLesson';

const C = {bg:'#101727', panel:'#1b2940', cyan:'#67e8f9', gold:'#fcd34d', violet:'#c4b5fd', ink:'#f8fafc'};
const label = {fontSize:27,letterSpacing:3,fontWeight:700} as const;
const RootOwnedTrace = () => null;

const ThinkingCard=({beat,lesson}:{beat:any,lesson:any})=>{
 const t=useCurrentFrame()/30;
 const waiting=t>=beat.speech_end;
 const progress=waiting?(t-beat.speech_end)/(beat.end-beat.speech_end):0;
 return <div style={{position:'absolute',left:76,right:150,top:410}}>
   <div style={{...label,color:C.cyan,marginBottom:28}}>{beat.kind==='hook'?'THE CHALLENGE':beat.kind==='prediction'?'MAKE A PREDICTION':'TRY IT FROM MEMORY'}</div>
   <div style={{fontSize:68,lineHeight:1.15,fontWeight:850}}>{beat.text}</div>
   {beat.kind==='hook'&&<div style={{marginTop:44,fontSize:53,color:C.gold,transform:`translateX(${6*Math.sin(t*3)}px)`}}>{lesson.values.join(' → ')} → null</div>}
   {beat.kind!=='hook'&&<div style={{marginTop:36,fontSize:29,color:C.violet}}>Think it through. Say your answer.</div>}
   {waiting&&<div style={{marginTop:24,height:7,background:C.panel}}><div style={{height:7,width:`${Math.min(100,progress*100)}%`,background:C.cyan}}/></div>}
 </div>;
};

export const PointerTrace: React.FC<{lesson:any,compact?:boolean}> = ({lesson,compact=false}) => {
  const t = useCurrentFrame()/30;
  const ev = [...lesson.events].reverse().find((e:any)=>e.time<=t) || lesson.events[0];
  const n = ev.node;
  const done = ev.action==='finish';
  const reversedCount = done ? lesson.values.length : n + (['reverse','advance'].includes(ev.action)?1:0);
  const current = done ? null : ev.action==='advance' ? n+1 : n;
  const prev = done ? lesson.values.length-1 : ev.action==='advance' ? n : n-1;
  const next = ['save','reverse','advance'].includes(ev.action) && n+1<lesson.values.length ? n+1 : null;
  const width=840, x=(i:number)=>100+i*(640/(lesson.values.length-1));
  const phase = {intro:'Keep access to every node',save:'1 / SAVE THE SUCCESSOR',reverse:'2 / REVERSE THE LINK',advance:'3 / ADVANCE BOTH POINTERS',finish:'RETURN PREVIOUS — THE NEW HEAD'}[ev.action as string];
  return <div style={{position:'absolute',left:70,top:compact?290:410,width,color:C.ink}}>
    <div style={{...label,color:C.cyan,fontSize:compact?25:30,marginBottom:30}}>{phase}</div>
    <svg width={840} height={compact?300:430} viewBox="0 0 840 400">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill={C.cyan}/></marker></defs>
      {lesson.values.map((v:number,i:number)=><g key={i}>
        {i>0 && i<reversedCount && <path d={`M ${x(i)-64} 190 L ${x(i-1)+70} 190`} stroke={C.cyan} strokeWidth={7} fill="none" markerEnd="url(#arrow)"/>}
        {i<lesson.values.length-1 && i>=reversedCount && <path d={`M ${x(i)+64} 190 L ${x(i+1)-70} 190`} stroke={C.cyan} strokeWidth={7} fill="none" markerEnd="url(#arrow)"/>}
        <rect x={x(i)-58} y={133} width={116} height={116} rx={25} fill={i<reversedCount?'#174956':C.panel} stroke={i===current?C.gold:C.cyan} strokeWidth={5}/>
        <text x={x(i)} y={209} textAnchor="middle" fontSize={53} fontWeight="800" fill="white">{v}</text>
        {i===current && <text x={x(i)} y={103} textAnchor="middle" fontSize={30} fill={C.gold}>current</text>}
        {i===prev && <text x={x(i)} y={299} textAnchor="middle" fontSize={30} fill={C.cyan}>previous</text>}
        {i===next && <text x={x(i)} y={345} textAnchor="middle" fontSize={30} fill={C.violet}>saved next</text>}
      </g>)}
      {reversedCount>0 && <><path d="M 55 235 L 22 355" stroke={C.cyan} strokeWidth={5}/><text x={5} y={390} fill={C.cyan} fontSize={23}>null</text></>}
      {!done && prev<0 && <text x={12} y={360} fill={C.cyan} fontSize={26}>previous = null</text>}
      {done && <text x={420} y={380} textAnchor="middle" fontSize={32} fill={C.gold}>{[...lesson.values].reverse().join(' → ')} → null</text>}
    </svg>
    {!compact && <div style={{background:C.panel,borderRadius:26,padding:'24px 30px',fontFamily:'monospace',fontSize:33,lineHeight:1.7}}>
      {['next = current.next','current.next = previous','previous = current','current = next'].map((line,i)=><div key={line} style={{color:(ev.action==='save'&&i===0)||(ev.action==='reverse'&&i===1)||(ev.action==='advance'&&i>=2)?C.gold:'#9caec7'}}>{line}</div>)}
    </div>}
  </div>;
};

const Captions = ({lesson}:{lesson:any}) => {
  const t=useCurrentFrame()/30;
  const group=lesson.captions.find((g:any)=>g.start<=t&&t<g.end);
  if(!group)return null;
  return <div style={{position:'absolute',left:78,right:150,top:lesson.format_id==='dialogue_gameplay'?800:1335,textAlign:'center',fontSize:62,fontWeight:850,lineHeight:1.22,textShadow:'0 4px 10px #000',WebkitTextStroke:'1.5px #0b1020'}}>
    <div style={{fontSize:24,letterSpacing:3,color:group.speaker==='peter'?C.gold:C.cyan,marginBottom:16,textTransform:'uppercase'}}>{group.speaker==='narrator'?'':group.speaker}</div>
    {group.words.map((w:any,i:number)=><span key={i} style={{color:t>=w.start&&t<w.end?C.gold:'white'}}>{w.text}{' '}</span>)}
  </div>;
};

const Character=({role,lesson,left}:{role:string,lesson:any,left:number})=>{
  const frame=useCurrentFrame(),t=frame/30;
  const seg=lesson.segments.find((s:any)=>s.speaker===role&&s.start<=t&&t<s.end);
  const amp=seg?seg.envelope[Math.floor((t-seg.start)*30)]||0:0;
  const active=amp>.025;
  return <div style={{position:'absolute',left,top:1160,width:360,height:460,transform:`translateY(${active?-Math.min(amp*18,8):0}px)`,filter:active?'drop-shadow(0 0 20px #67e8f9)':'none'}}>
    {lesson.characters?.[role]?<Img src={staticFile(lesson.characters[role])} style={{width:'100%',height:420,objectFit:'contain',opacity:seg?1:.83}}/>:
      <div style={{height:370,borderRadius:'45%',background:role==='peter'?'#f0c48b':'#f9e296',border:'8px solid #162033',textAlign:'center',paddingTop:110,fontSize:90}}>•  •<div style={{margin:'20px auto',width:70,height:active?30:7,background:'#402d2d',borderRadius:20}}/></div>}
    {lesson.characters?.[role]&&active&&<svg viewBox={role==='peter'?'0 0 247 359':'0 0 242 273'}
      preserveAspectRatio="xMidYMid meet" style={{position:'absolute',left:0,top:0,width:'100%',height:420,pointerEvents:'none'}}>
      <ellipse cx={role==='peter'?137:128} cy={role==='peter'?54:114}
        rx={role==='peter'?16:9} ry={Math.min(role==='peter'?8:6,2+amp*18)}
        fill="#512a2d" stroke="#50382d" strokeWidth="1"/>
      {amp>.12&&<ellipse cx={role==='peter'?137:128} cy={role==='peter'?57:116}
        rx={role==='peter'?8:4} ry={2} fill="#e69095"/>}
    </svg>}
    <div style={{textAlign:'center',fontSize:30,fontWeight:800,color:role==='peter'?C.gold:C.cyan,textTransform:'uppercase'}}>{role}</div>
  </div>;
};

const SyntheticBackground=()=>{
 const f=useCurrentFrame();
 return <AbsoluteFill style={{background:'linear-gradient(#1d4b62,#152c3b 55%,#0d1929)'}}>
   {Array.from({length:12},(_,i)=><div key={i} style={{position:'absolute',left:((i*219)%1050)-80,top:((i*209+f*5)%2200)-200,width:200,height:90,background:i%2?'#367e60':'#418f70',borderBottom:'30px solid #374744',transform:'skewY(-9deg)',opacity:.5}}/>)}
 </AbsoluteFill>
};

const Lesson=({lesson}:{lesson:any})=>{
 const frame=useCurrentFrame(); const {durationInFrames}=useVideoConfig();
 const dialogue=lesson.format_id==='dialogue_gameplay';
 const beat=lesson.teaching_beats?.find((b:any)=>b.start<=frame/30&&frame/30<b.end);
 const thinking=beat&&['hook','prediction','retrieval'].includes(beat.kind);
 // Legacy packs keep their prior appearance. New packs explicitly choose the experiment.
 const gameplay=dialogue&&lesson.background_mode!=='concept_only';
 return <AbsoluteFill style={{background:C.bg,color:C.ink,fontFamily:'DejaVu Sans, sans-serif'}}>
   {gameplay && (lesson.background?<OffthreadVideo src={staticFile(lesson.background)} muted style={{width:'100%',height:'100%',objectFit:'cover'}}/>:<SyntheticBackground/>)}
   {gameplay&&<AbsoluteFill style={{background:'linear-gradient(#07101ad9,transparent 35%,#07101a66 60%,#07101acc)'}}/>}
   <div style={{position:'absolute',left:76,top:128,right:150}}>
     <div style={{...label,color:C.cyan,marginBottom:25}}>POINTER LAB / {dialogue?'THE CONVERSATION':'THE VISUAL EXPLANATION'}</div>
     <div style={{fontSize:thinking?46:60,lineHeight:1.08,fontWeight:850,letterSpacing:-2}}>{lesson.title}</div>
   </div>
   {thinking?<ThinkingCard beat={beat} lesson={lesson}/>:<PointerTrace lesson={lesson} compact={dialogue}/>}
   {lesson.custom_scene&&!dialogue&&!thinking&&<AbsoluteFill style={{clipPath:'inset(300px 150px 1530px 70px)',overflow:'hidden',contain:'paint'}}>
     <CustomScene lesson={lesson} components={{PointerTrace:RootOwnedTrace}}/>
   </AbsoluteFill>}
   <Captions lesson={lesson}/>
   {dialogue&&<><Character role="peter" lesson={lesson} left={65}/><Character role="stewie" lesson={lesson} left={550}/></>}
   {!dialogue&&!thinking&&<div style={{position:'absolute',left:76,top:1190,right:150,color:C.violet,fontSize:34}}>{beat?.text || (lesson.teaching_beats?.length?'Follow the highlighted pointer.':'Save → reverse → advance. Never lose the unprocessed suffix.')}</div>}
   <div style={{position:'absolute',left:76,bottom:250,color:'#c0cddd',fontSize:23}}>{lesson.disclosure}</div>
   <div style={{position:'absolute',left:76,bottom:214,width:850,height:6,background:'#334155'}}><div style={{width:`${100*frame/durationInFrames}%`,height:6,background:C.cyan}}/></div>
   <Audio src={staticFile('narration.wav')}/>
 </AbsoluteFill>
};
const Presentation=({lesson}:{lesson:any})=>lesson.format_id==='math_explainer'?<MathLesson lesson={lesson}/>:['reference_v2','reference_v3'].includes(lesson.presentation)?<ReferenceLesson lesson={lesson}/>:<Lesson lesson={lesson}/>;
const Root=()=> <Composition id="Lesson" component={Presentation} width={1080} height={1920} fps={30} durationInFrames={1350} calculateMetadata={({props})=>({durationInFrames:props.lesson.frame_count})}/>;
registerRoot(Root);
