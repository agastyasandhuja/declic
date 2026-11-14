import {PopCaptions} from './PopCaptions';
import React,{useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,Audio,Composition,Sequence,continueRender,delayRender,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import {createWorld} from './World';
import {lakeCaptionTop} from './ShotDirection';

const Movie=({lesson}:{lesson:any})=>{
 const frame=useCurrentFrame(),t=frame/30,canvas=useRef<HTMLCanvasElement>(null),world=useRef<any>(null);
 const [ready]=useState(()=>delayRender('Build deterministic voxel world'));
 const beat=lesson.segments.find((b:any)=>t>=b.start&&t<b.end)||lesson.segments.at(-1);
 useLayoutEffect(()=>{world.current=createWorld(canvas.current!,lesson.words);world.current.update(beat,(t-beat.start)/(beat.end-beat.start),t);continueRender(ready);return()=>world.current?.dispose()},[]);
 useLayoutEffect(()=>{world.current?.update(beat,(t-beat.start)/(beat.end-beat.start),t)},[frame]);
 return <AbsoluteFill style={{background:'#8dc6ef'}}>
  <canvas ref={canvas} width={720} height={1280} style={{width:720,height:1280}}/>
  <PopCaptions words={lesson.words} now={t} top={lakeCaptionTop(beat.scene)}/>
  {lesson.segments.map((s:any,i:number)=><Sequence key={i} from={Math.round(s.start*30)} durationInFrames={Math.ceil(s.duration*30)}><Audio src={staticFile(`${lesson.id}/assets/${s.audio}`)}/></Sequence>)}
  <Audio src={staticFile(`${lesson.id}/assets/ambience.wav`)} volume={.4}/>
 </AbsoluteFill>;
};
registerRoot(()=> <Composition id="VoxelStory" component={Movie} width={720} height={1280} fps={30} durationInFrames={1500} calculateMetadata={({props})=>({durationInFrames:props.lesson.frames})}/>);
