import React,{useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,Audio,Composition,Sequence,continueRender,delayRender,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import {PopCaptions} from './PopCaptions';
import {createShop} from './World';
const Movie=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30,canvas=useRef<HTMLCanvasElement>(null),world=useRef<any>(null);
 const [handle]=useState(()=>delayRender('Build Jensen shop and attached props'));
 useLayoutEffect(()=>{world.current=createShop(canvas.current!,lesson);world.current.update(t);continueRender(handle);return()=>world.current?.dispose()},[]);
 useLayoutEffect(()=>{world.current?.update(t)},[t]);
 return <AbsoluteFill style={{background:'#19252a'}}>
  <canvas ref={canvas} width={1080} height={1920}/>
  <PopCaptions words={lesson.words} now={t} top={1510}/>
  {lesson.segments.map((s:any,i:number)=><Sequence key={i} from={Math.round(s.start*30)} durationInFrames={Math.ceil(s.duration*30)}><Audio src={staticFile(`${lesson.id}/assets/${s.audio}`)}/></Sequence>)}
 </AbsoluteFill>
};
registerRoot(()=> <Composition id="DemoLesson" component={Movie} width={1080} height={1920} fps={30} durationInFrames={1350} calculateMetadata={({props})=>({durationInFrames:props.lesson.frames})}/>);
