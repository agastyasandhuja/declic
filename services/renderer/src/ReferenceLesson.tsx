import {PopCaptions} from './PopCaptions';
import React from 'react';
import {AbsoluteFill, Audio, Img, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {SpaceScenesV3} from './SpaceScenesV3';
import {SpaceScene} from './SpaceScene';
import {PaymentScene} from './PaymentScenes';
import {DecisionScene} from './DecisionScenes';

const clamp=(n:number)=>Math.max(0,Math.min(1,n));
const ImageShot=({shot,images,dialogue=false}:{shot:any,images:any,dialogue?:boolean})=>{
 const t=useCurrentFrame()/30,p=clamp((t-shot.start)/(shot.end-shot.start));
 const selected=shot.asset_ids.map((id:string)=>images[id]).filter(Boolean);
 const scale=shot.camera==='pull'?1.2-p*.17:1.02+p*.16;
 const x=shot.camera==='pan_left'?30-p*60:shot.camera==='pan_right'?-30+p*60:0;
 return <AbsoluteFill style={dialogue?{inset:'470px 100px 700px 70px',borderRadius:16,overflow:'hidden',boxShadow:'0 10px 45px #0008'}:{overflow:'hidden'}}>
  {selected.map((image:any,i:number)=>{const framing=image.framing?.[shot.shot_id];
   const imageScale=framing?framing.zoom_start+(framing.zoom_end-framing.zoom_start)*p:scale;
   // A normalized focal point is centered in the crop, not aligned to the same
   // percentage of the viewport (CSS object-position has different semantics).
   const paneWidth=(dialogue?910:1080)/(selected.length>1?2:1),paneHeight=dialogue?750:1920;
   const coverScale=Math.max(paneWidth/image.width,paneHeight/image.height);
   const positionAxis=(focus:number,pane:number,size:number)=>size<=pane?50:clamp((pane/2-focus*size)/(pane-size))*100;
   const position=framing&&framing.fit==='cover'?`${positionAxis(framing.focus_x,paneWidth,image.width*coverScale)}% ${positionAxis(framing.focus_y,paneHeight,image.height*coverScale)}%`:'50% 50%';
   return <AbsoluteFill key={image.file} style={selected.length>1?{left:i?'50%':0,width:'50%',overflow:'hidden'}:{}}>
   <Img src={staticFile(image.file)} style={{width:'100%',height:'100%',objectFit:'cover',filter:'blur(28px) brightness(.4)',transform:'scale(1.2)'}}/>
   <Img src={staticFile(image.file)} style={{position:'absolute',width:'100%',height:'100%',objectFit:dialogue?'contain':(framing?.fit||'cover'),objectPosition:position,transform:`translateX(${x}px) scale(${imageScale})`}}/>
  </AbsoluteFill>;})}
 </AbsoluteFill>;
};

// The arrows are driven only by the validated semantic trace, never by model-written code.
const Diagram=({lesson,shot}:{lesson:any,shot:any})=>{
 const t=useCurrentFrame()/30,p=clamp((t-shot.start)/(shot.end-shot.start));
 const verified=[...lesson.trace].reverse().find((s:any)=>s.time<=t)||lesson.trace[0];
 const mistake=shot.diagram_demo==='broken_first_link';
 const state=mistake?{...lesson.trace[0],links:lesson.trace[0].links.map((next:any,i:number)=>i===0?null:next)}:verified;
 const linked=lesson.trace_kind==='linked_list_reverse'&&state;
 const values=linked?lesson.values:shot.labels;
 const width=850,spacing=values.length>1?650/(values.length-1):0,x=(i:number)=>values.length===1?425:100+i*spacing;
 return <div style={{position:'absolute',left:70,right:110,top:530,height:630,transform:`scale(${1+p*.035})`,transformOrigin:'center'}}>
  <div style={{height:630,background:lesson.format_id==='dialogue_gameplay'?'transparent':'#071827c9',borderRadius:16,filter:lesson.format_id==='dialogue_gameplay'?'drop-shadow(0 3px 5px #000)':'none',color:'#fff'}}>
   {(shot.headline||mistake)&&<div style={{padding:'40px 35px 0',fontSize:42,fontWeight:800,textAlign:'center'}}>{mistake?"Peter’s wrong move":shot.headline}</div>}
   {linked?<svg viewBox={`0 0 ${width} 460`} style={{width:'100%',height:450}}>
    <defs><marker id="trace-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#5ff3e4"/></marker></defs>
    {state.links.map((next:number|null,i:number)=>next===null?null:<path key={i} d={`M${x(i)+(next>i?62:-62)} 205 L${x(next)+(next>i?-70:70)} 205`} stroke="#5ff3e4" strokeWidth="7" fill="none" markerEnd="url(#trace-arrow)"/>)}
    {values.map((v:number,i:number)=><g key={i}>
      <circle cx={x(i)} cy={205} r={59} fill={mistake&&i>0?'#526173':state.current===i?'#ffdd54':'#d7f3ef'} stroke="#5ff3e4" strokeWidth="5"/>
      <text x={x(i)} y={224} textAnchor="middle" fontSize="57" fontWeight="800" fill="#102931">{v}</text>
      {state.action==='finish'&&state.head===i&&<text x={x(i)} y={70} textAnchor="middle" fontSize="34" fill="#ffe374">new head</text>}
      {mistake&&i>0&&<text x={x(i)} y={107} textAnchor="middle" fontSize="28" fill="#ff9399">unreachable</text>}
      {state.current===i&&<text x={x(i)} y={107} textAnchor="middle" fontSize="34" fill="currentColor">current</text>}
      {state.previous===i&&<text x={x(i)} y={321} textAnchor="middle" fontSize="34" fill="currentColor">previous</text>}
      {state.saved_next===i&&<text x={x(i)} y={373} textAnchor="middle" fontSize="34" fill="currentColor">saved next</text>}
      {state.links[i]===null&&<text x={x(i)} y={432} textAnchor="middle" fontSize="34" fill="currentColor">next → None</text>}
    </g>)}
   </svg>:<div style={{display:'flex',flexDirection:'column',gap:28,padding:'45px 50px'}}>{values.map((v:string,i:number)=><div key={i} style={{fontSize:46,fontWeight:750,opacity:clamp((p*values.length-i+.8)*2),transform:`translateX(${(1-clamp(p*values.length-i+1))*35}px)`,borderLeft:'6px solid #56dbef',paddingLeft:25}}>{v}</div>)}</div>}
   {linked&&<div style={{position:'absolute',left:25,right:25,bottom:18,display:'flex',justifyContent:'center',gap:20,fontSize:34,color:'#bceeff'}}>
    {state.previous===null&&<span>previous = None</span>}
    {state.current===null&&<span>current = None</span>}
    {state.saved_next===null&&['save','reverse','advance','finish'].includes(state.action)&&<span>saved next = None</span>}
   </div>}
  </div>
 </div>;
};

const WordCaptions=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30;
 const caption=lesson.captions.find((g:any)=>g.start<=t&&t<g.end);
 return <PopCaptions caption={caption} now={t} top={lesson.format_id==='dialogue_gameplay'?235:1450}/>;
};
const ActiveCharacter=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30,segment=lesson.segments.find((s:any)=>s.start<=t&&t<s.end)||lesson.segments.at(-1);
 const role=segment.speaker,image=lesson.characters?.[role],amp=segment.envelope[Math.floor((t-segment.start)*30)]||0;
 if(!image)return null;
 const entrance=clamp((t-segment.start)*6);
 return <div style={{position:'absolute',left:30,top:1210,width:role==='peter'?450:430,height:555,transform:`translateX(${(1-entrance)*40}px) translateY(${-Math.min(6,amp*14)}px) rotate(${Math.sin(t*2)*.5}deg)`,filter:'drop-shadow(3px 8px 7px #0008)'}}>
  <Img src={staticFile(image)} style={{width:'100%',height:'100%',objectFit:'contain',objectPosition:'bottom left'}}/>
 </div>;
};

export const ReferenceLesson=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30;
 const shot=lesson.shots.find((s:any)=>s.start<=t&&t<s.end)||lesson.shots.at(-1);
 const dialogue=lesson.format_id==='dialogue_gameplay',space=lesson.format_id==='space_explainer';
 const image=lesson.images?.[shot.asset_ids?.[0]];
 const shotAge=t-shot.start;
 return <AbsoluteFill style={{background:'#05101d',fontFamily:'DejaVu Sans,sans-serif',color:'#fff',overflow:'hidden'}}>
  {dialogue&&lesson.background&&<OffthreadVideo src={staticFile(lesson.background)} muted style={{width:'100%',height:'100%',objectFit:'cover'}}/>}
  {dialogue&&<AbsoluteFill style={{background:'linear-gradient(#0004,transparent 24%,transparent 72%,#0003)'}}/>}
  {space&&shot.kind!=='image'&&(lesson.presentation==='reference_v3'?<SpaceScenesV3 shot={shot}/>:<SpaceScene shot={shot} images={lesson.images}/>)}
  {!dialogue&&!space&&<AbsoluteFill style={{background:lesson.installment_example?'#08090e':'radial-gradient(ellipse at 50% 45%,#17526d,#040d18 75%)'}}/>}
  {shot.kind==='image'&&<ImageShot shot={shot} images={lesson.images} dialogue={dialogue}/>}
  {shot.kind==='image'&&(shot.headline||shot.labels.length>0)&&<div style={{position:'absolute',left:85,right:120,top:dialogue?460:320,textAlign:'center',textShadow:'0 3px 8px #000,0 0 30px #000',background:'#07101df2',padding:'25px 24px',borderRadius:14}}>
   <div style={{fontSize:dialogue?38:48,fontWeight:800,lineHeight:1.15}}>{shot.headline}</div>
   <div style={{fontSize:dialogue?31:39,color:'#ffdf82',lineHeight:1.5,marginTop:12}}>{shot.labels.map((label:string,i:number)=><div key={i}>{label}</div>)}</div>
  </div>}
  {shot.kind==='diagram'&&(lesson.installment_example?<PaymentScene lesson={lesson} shot={shot}/>:shot.motion_scene&&shot.motion_scene!=='none'?<DecisionScene shot={shot}/>:<Diagram lesson={lesson} shot={shot}/>)}
  {shot.kind==='kinetic'&&<div style={{position:'absolute',top:580,left:80,right:120,textAlign:'center',fontSize:83,lineHeight:1.08,fontWeight:850,textShadow:'0 6px 25px #000',transform:`scale(${.94+.06*clamp(shotAge*4)})`}}>{shot.headline}<div style={{fontSize:54,color:'#81e9f5',marginTop:36,lineHeight:1.5}}>{shot.labels.map((label:string,i:number)=><div key={i}>{label}</div>)}</div></div>}
  {space&&lesson.presentation!=='reference_v3'&&shot.kind==='space'&&shot.headline&&<div style={{position:'absolute',left:90,right:120,top:330,textAlign:'center',fontSize:46,fontWeight:650,letterSpacing:1,opacity:clamp(shotAge*2)*Math.min(1,(shot.end-t)*2),textShadow:'0 4px 15px #000'}}>{shot.headline}</div>}
  {dialogue&&<ActiveCharacter lesson={lesson}/>}
  <WordCaptions lesson={lesson}/>

  <Audio src={staticFile('narration.wav')}/>
 </AbsoluteFill>;
};
