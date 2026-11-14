import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';

const clamp=(v:number)=>Math.min(1,Math.max(0,v));
const ease=(v:number)=>{v=clamp(v);return v*v*(3-2*v)};
const lerp=(a:number,b:number,p:number)=>a+(b-a)*p;
const purple='#bca1ff',gold='#f6d78e',white='#f5f3ee';
const Label=({x,y,children,size=78,color=white,opacity=1}:any)=><text x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize={size} fill={color} opacity={opacity}>{children}</text>;

/** A rigid dissection, not a morph: each triangle keeps its two leg lengths.
 * Endpoints tile the same (a+b) square. Transient overlaps are never labelled c².
 */
export const PythagoreanLesson=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30;
 const {a,b,c_squared}=lesson.math;
 const side=a+b,unit=780/side,A=a*unit,B=b*unit,S=780;
 const assembly=ease((t-3)/2.1);
 const squareVisible=ease((t-3.1)/1.0),areaLabel=ease((t-6.1)/.5)*(1-ease((t-9)/.3));
 const finalLabels=ease((t-13.5)/.6),identity=ease((t-17.7)/.6);
 const starts=[[0,0],[S,0],[S,S],[0,S]];
 const ends=[[0,A],[S,0],[A,S],[A,A]];
 const left=150,top=580;
 const initialScale=Math.min(1.55,650/Math.max(A,B));
 const firstX=(S-A*initialScale)/2,firstY=(S-B*initialScale)/2;
 const c=Math.sqrt(c_squared),exactRoot=Number.isInteger(c)?String(c):`√${c_squared}`;
 return <AbsoluteFill style={{background:'#030303',fontFamily:'DejaVu Serif,serif'}}>
  <svg width="1080" height="1920" viewBox="0 0 1080 1920">
   <g transform={`translate(0 ${-7*Math.sin(Math.PI*ease(t/.7))})`}>
    <text x="540" y="310" textAnchor="middle" fontSize="89" fill={white}>
     <tspan fill={purple}>a²</tspan> + <tspan fill={gold}>b²</tspan> = {identity>.5?'c²':'?'}
    </text>
   </g>
   <g transform={`translate(${left} ${top})`}>
    {/* These exact areas remain behind congruent triangles; only their tiling changes. */}
    <rect width={S} height={S} fill={purple} opacity={squareVisible*.24}/>
    <rect x={A} y={A} width={B} height={B} fill={gold} opacity={finalLabels*.24}/>
    <rect width={S} height={S} fill="none" stroke={white} strokeWidth="3" opacity={squareVisible*.7}/>
    {starts.map(([sx,sy],i)=>{
     const move=i===1?0:ease((t-9.5-(i===3?.5:i===2?.25:0))/2.8);
     const x=lerp(sx,ends[i][0],move),y=lerp(sy,ends[i][1],move);
     const arrive=ease((t-3.3-i*.32)/.8);
     const px=i===0?lerp(firstX,x,assembly):x;
     const py=i===0?lerp(firstY,y,assembly):y+(1-arrive)*48;
     const scale=i===0?lerp(initialScale,1,assembly):.9+.1*arrive;
     return <g key={i} opacity={i===0?1:arrive} transform={`translate(${px} ${py}) rotate(${i*90}) scale(${scale})`}>
      <path d={`M0 0 L${A} 0 L0 ${B} Z`} fill="#24232e" stroke="#e2ddea" strokeWidth={3/scale} strokeLinejoin="round"/>
      <path d="M0 22 H22 V0" fill="none" stroke={white} strokeWidth={2/scale} opacity=".55"/>
      {i===0&&<g opacity={1-assembly}>
       <Label x={A/2} y={-35} size={52/scale} color={purple}>a</Label>
       <Label x={-35} y={B/2} size={52/scale} color={gold}>b</Label>
       <Label x={A/2+36} y={B/2+28} size={52/scale}>c</Label>
      </g>}
     </g>;
    })}
    <polygon points={`${A},0 ${S},${A} ${B},${S} 0,${B}`} fill="none" stroke={purple} strokeWidth="5" pathLength="1" strokeDasharray="1" strokeDashoffset={1-ease((t-5.9)/1.0)} opacity={areaLabel}/>
    <Label x={S/2} y={S/2} size={120} color={purple} opacity={areaLabel}>c²</Label>
    <Label x={A/2} y={A/2} size={Math.min(100,A*.45)} color={purple} opacity={finalLabels}>a²</Label>
    <Label x={A+B/2} y={A+B/2} size={Math.min(100,B*.45)} color={gold} opacity={finalLabels}>b²</Label>
   </g>
   {/* The numeric example lands only after the visual area argument is complete. */}
   <g opacity={identity} transform={`translate(0 ${18*(1-identity)})`}>
    <text x="540" y="1535" textAnchor="middle" fontSize="78" fill={white}>
     <tspan fill={purple}>{a}²</tspan> + <tspan fill={gold}>{b}²</tspan> = {exactRoot.includes('√')?`(${exactRoot})²`:`${exactRoot}²`}
    </text>
    <Label x={540} y={1650} size={58} opacity={ease((t-19)/.7)}>{a*a} + {b*b} = {c_squared}</Label>
   </g>
   <path d="M290 1730 H790" stroke={purple} strokeWidth="3" pathLength="1" strokeDasharray="1" strokeDashoffset={1-ease((t-20.2)/.8)} opacity={identity}/>
  </svg>
  <Audio src={staticFile(lesson.audio_file)}/>
 </AbsoluteFill>;
};
