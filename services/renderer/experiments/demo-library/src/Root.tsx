import React,{useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,Audio,Composition,Img,Sequence,continueRender,delayRender,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import {PopCaptions} from './PopCaptions';
import {createWorld} from './World';
const C=['#82d5ce','#efbb76','#b5a2e8','#f19c9a','#99b5e3','#c6d497','#e7b6ce','#a7c7c9','#d6c6a7'];
const ease=(x:number)=>{const p=Math.max(0,Math.min(1,x));return p*p*(3-2*p)};
const xy=(node:any,p:number)=>({x:100+(node.x+((node.to_x??node.x)-node.x)*p)*880,y:300+(node.y+((node.to_y??node.y)-node.y)*p)*850});
const Person=({color,target,moving,p}:{color:string,target:any,moving:boolean,p:number})=>{
 const face=target&&target.x<0?-1:1;const tx=target?Math.abs(target.x):80,ty=target?target.y:90;
 // A two-link arm reaches the nearest prop's edge only while it is in range.
 // Fixed lengths preserve contact; no perpetual waving substitutes for action.
 const reach=target&&Math.hypot(tx-28,ty-15)<180;
 const dx=reach?Math.max(15,tx-50)-28:30,dy=reach?ty-15:85;
 const length=Math.max(15,Math.min(109,Math.hypot(dx,dy)));
 const angle=Math.atan2(dy,dx),bend=Math.acos(Math.max(-1,Math.min(1,(55*55+length*length-55*55)/(110*length))));
 const ex=28+55*Math.cos(angle+bend),ey=15+55*Math.sin(angle+bend);
 const hx=28+length*Math.cos(angle),hy=15+length*Math.sin(angle);
 const stride=moving?10*Math.sin(p*Math.PI*4):0;
 return <g transform={`scale(${face},1)`}>
 <path d="M -28 15 L -43 70 L -42 115" fill="none" stroke="#d19c76" strokeWidth={18} strokeLinecap="round"/>
 <path d={`M -17 87 L ${-25-stride} 162 M 17 87 L ${26+stride} 162`} stroke="#7594b5" strokeWidth={23} strokeLinecap="round"/>
 <rect x={-35} y={-2} width={70} height={100} rx={24} fill={color}/><circle cy={-43} r={35} fill="#e0ae86"/><path d="M -32 -53 Q -30 -96 31 -62" fill="#433d3b"/>
 <circle cx={17} cy={-47} r={3} fill="#263346"/><path d="M 29 -45 L 39 -35 L 29 -32" fill="#e0ae86"/><path d="M 15 -26 Q 23 -22 31 -29" fill="none" stroke="#744c41" strokeWidth={3}/>
 <path d={`M 28 15 L ${ex} ${ey} L ${hx} ${hy}`} fill="none" stroke="#e0ae86" strokeWidth={18} strokeLinecap="round"/>
 </g>};
const Matrices=({scene,p}:{scene:any,p:number})=>{
 const a=scene.matrix_a,b=scene.matrix_b;if(!a?.length)return null;
 const result=a.map((row:number[])=>b[0].map((_:number,j:number)=>row.reduce((s:number,v:number,k:number)=>s+v*b[k][j],0)));
 const current=Math.min(result.length*result[0].length-1,Math.floor(p*result.length*result[0].length));const row=Math.floor(current/result[0].length),col=current%result[0].length;
 const matrix=(values:number[][],x:number,y:number,which:string)=><g transform={`translate(${x},${y})`}><path d={`M 10 -30 H -8 V ${values.length*85-25} H 10 M ${values[0].length*85-20} -30 H ${values[0].length*85} V ${values.length*85-25} H ${values[0].length*85-20}`} fill="none" stroke="#e7e9f1" strokeWidth={4}/>{values.map((r,i)=>r.map((v,j)=><text key={`${i}-${j}`} x={j*85+32} y={i*85+20} textAnchor="middle" fontSize={54} fill={(which==='a'&&i===row)||(which==='b'&&j===col)?'#efbb76':which==='result'&&i*values[0].length+j<=current?'#82d5ce':'#f2f0eb'} opacity={which==='result'&&i*values[0].length+j>current?.18:1}>{v}</text>))}</g>;
 return <svg width={1080} height={1920}>{matrix(a,150,420,'a')}<text x={515} y={490} fill="white" fontSize={72}>×</text>{matrix(b,640,420,'b')}
 <text x={540} y={850} fill="#efbb76" fontSize={44} textAnchor="middle">{a[row].map((v:number,k:number)=>`${v}×${b[k][col]}`).join(' + ')} = {result[row][col]}</text>{matrix(result,400,1040,'result')}</svg>
};
const Diagram=({scene,style,u}:{scene:any,style:string,u:number})=>{
 const p=ease((u-.15)/.65);if(scene.matrix_a?.length)return <Matrices scene={scene} p={p}/>;
 const nodes=scene.nodes.map((n:any)=>({...n,moving:Math.abs((n.to_x??n.x)-n.x)+Math.abs((n.to_y??n.y)-n.y)>.01,...xy(n,p)}));
 return <svg width={1080} height={1920}>
 <defs><marker id="arrow" viewBox="0 0 10 10" refX={8} refY={5} markerWidth={6} markerHeight={6} orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8fa9bc"/></marker></defs>
 {scene.kind==='timeline'&&<path d="M 160 840 H 920" stroke="#738da6" strokeWidth={5} markerEnd="url(#arrow)"/>}
 {scene.kind==='balance'&&<g stroke="#9aaac1" strokeWidth={8}><path d="M 540 560 V 1180 M 380 1180 H 700 M 240 670 H 840"/><path d="M 260 670 L 200 1020 H 420 L 360 670 M 720 670 L 660 1020 H 880 L 820 670" fill="none"/></g>}
 {scene.edges.map((e:any,i:number)=>{const a=nodes.find((n:any)=>n.id===e.source),b=nodes.find((n:any)=>n.id===e.target);return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#8fa9bc" strokeWidth={5} markerEnd="url(#arrow)"/>})}
 {nodes.map((n:any,i:number)=><g key={n.id} transform={`translate(${n.x},${n.y})`}>
 {n.glyph==='person'?<Person color={C[i%9]} p={p} moving={n.moving&&u>.15&&u<.8} target={(()=>{const targets=nodes.filter((other:any)=>other.glyph!=='person');targets.sort((a:any,b:any)=>Math.hypot(a.x-n.x,a.y-n.y)-Math.hypot(b.x-n.x,b.y-n.y));return targets.length?{x:targets[0].x-n.x,y:targets[0].y-n.y}:null})()}/>:n.glyph==='circle'||n.glyph==='coin'?<circle r={n.glyph==='coin'?42:53} fill={n.glyph==='coin'?'#edc86f':'#192d43'} stroke={C[i%9]} strokeWidth={5}/>:<g><rect x={-65} y={-45} width={130} height={90} rx={n.glyph==='box'?18:4} fill={style==='cartoon'?C[i%9]:'#24394d'} stroke={C[i%9]} strokeWidth={4}/>{n.glyph==='crate'&&<path d="M -55 -35 L 55 35 M -55 35 L 55 -35" stroke="#6e5745" strokeWidth={5}/>} {n.glyph==='book'&&<path d="M -45 -25 H 48 M -45 -6 H 48 M -45 13 H 25" stroke="#e9e0ce" strokeWidth={5}/>}</g>}
 {n.value&&<text textAnchor="middle" y={12} fontSize={n.value.length>7?27:39} fill={n.glyph==='coin'?'#443720':'#fff8e9'} fontWeight={700}>{n.value}</text>}
 {n.label&&<text textAnchor="middle" y={n.glyph==='person'?209:98} fontSize={n.label.length>16?27:32} fill="#e4e7ef">{n.label}</text>}
 </g>)}
 {scene.equation&&<text x={540} y={1280} textAnchor="middle" fill="#efbb76" fontSize={scene.equation.length>36?32:45}>{scene.equation}</text>}
 </svg>
};
const Three=({scene,u,t}:{scene:any,u:number,t:number})=>{const ref=useRef<HTMLCanvasElement>(null),world=useRef<any>(null);const [handle]=useState(()=>delayRender('Build authored demo geometry'));
 useLayoutEffect(()=>{world.current=createWorld(ref.current!);world.current.update(scene,u,t);continueRender(handle);return()=>world.current?.dispose()},[]);
 useLayoutEffect(()=>{world.current?.update(scene,u,t)},[scene,u,t]);return <canvas ref={ref} width={1080} height={1920} style={{width:1080,height:1920}}/>};
const Movie=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30;const segment=lesson.segments.find((s:any)=>s.start<=t&&t<s.end)||lesson.segments.filter((s:any)=>s.start<=t).at(-1)||lesson.segments[0];
 const u=Math.max(0,Math.min(1,(t-segment.start)/(segment.end-segment.start)));const dialogue=lesson.format_style==='dialogue';
 return <AbsoluteFill style={{background:lesson.format_style==='cartoon'?'#253447':'#101c2d',fontFamily:'DejaVu Sans,sans-serif'}}>
 {lesson.format_style==='three_d'?<Three scene={segment.scene} u={u} t={t}/>:<div style={{position:'absolute',inset:0,transform:dialogue?'translateY(-215px) scale(.8)':'none',transformOrigin:'center 500px'}}><Diagram scene={segment.scene} style={lesson.format_style} u={u}/></div>}
 {dialogue&&Object.entries(lesson.characters).map(([role,name])=>{const speaking=segment.speaker_role===role&&t<segment.end;const amp=speaking?segment.envelope[Math.floor((t-segment.start)*30)]||0:0;return <Img key={role} src={staticFile(`${lesson.id}/assets/${name}`)} style={{position:'absolute',left:role==='peter'?60:570,top:1000,width:420,height:520,objectFit:'contain',opacity:speaking?1:.77,transform:`translateY(${-Math.min(8,amp*15)}px)`}}/>})}
 <PopCaptions words={lesson.words} now={t} top={dialogue?1530:1470}/>
 {lesson.segments.map((s:any,i:number)=><Sequence key={i} from={Math.round(s.start*30)} durationInFrames={Math.ceil(s.duration*30)}><Audio src={staticFile(`${lesson.id}/assets/${s.audio}`)}/></Sequence>)}
 </AbsoluteFill>
};
registerRoot(()=> <Composition id="DemoLesson" component={Movie} width={1080} height={1920} fps={30} durationInFrames={1350} calculateMetadata={({props})=>({durationInFrames:props.lesson.frames})}/>);
