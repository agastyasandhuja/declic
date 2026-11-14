import React from 'react';
import {useCurrentFrame} from 'remotion';

const white='#fff9ef', gold='#ffe15b', red='#ff777a', mint='#95f0c5';
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const ease=(x:number)=>{x=clamp(x);return x*x*(3-2*x);};
const Label=({x,y,children,size=58,color=white}:any)=><text x={x} y={y} fill={color} fontSize={size} textAnchor="middle" dominantBaseline="middle" fontFamily="DejaVu Sans,sans-serif" fontWeight="800" stroke="#080b13" strokeWidth="7" paintOrder="stroke">{children}</text>;

// All geometry is transparent. Only the objects themselves cast a dark shadow
// so they remain legible over gameplay, without reinstating a diagram panel.
const Ticket=({x=540,y=755,scale=1,cross=0}:any)=><g transform={`translate(${x} ${y}) scale(${scale})`}>
 <path d="M-290 -125 H290 V-45 C250 -45 250 45 290 45 V125 H-290 V45 C-250 45 -250 -45 -290 -45 Z" stroke={gold} strokeWidth="9" fill="none"/>
 <path d="M175 -125 V125" stroke={gold} strokeWidth="4" strokeDasharray="12 13"/>
 <Label x={-40} y={5} size={122} color={gold}>$20</Label>
 {cross>0&&<path d="M-220 95 L125 -95" stroke={red} strokeWidth="15" strokeLinecap="round" pathLength="1" strokeDasharray="1" strokeDashoffset={1-cross}/>}
</g>;

const Clock=({x=540,y=740,r=175,progress=0,color=gold}:any)=>{
 const a=progress*2*Math.PI-Math.PI/2;
 return <g>
  <circle cx={x} cy={y} r={r} fill="none" stroke={color} strokeWidth="9"/>
  {Array.from({length:12},(_,i)=>{const q=i*Math.PI/6;return <path key={i} d={`M${x+Math.sin(q)*(r-10)} ${y-Math.cos(q)*(r-10)} L${x+Math.sin(q)*(r-25)} ${y-Math.cos(q)*(r-25)}`} stroke={color} strokeWidth="5" strokeLinecap="round"/>;})}
  <path d={`M${x} ${y} L${x+Math.cos(a)*r*.73} ${y+Math.sin(a)*r*.73} M${x} ${y} L${x+r*.33} ${y-r*.24}`} fill="none" stroke={white} strokeWidth="10" strokeLinecap="round"/>
  <circle cx={x} cy={y} r="11" fill={white}/>
 </g>;
};

const Arrow=({d,color=white,progress=1}:any)=><path d={d} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" pathLength="1" strokeDasharray="1" strokeDashoffset={1-progress}/>;

export const DecisionScene=({shot}:{shot:any})=>{
 const t=useCurrentFrame()/30,elapsed=Math.max(0,t-shot.start);
 const p=clamp(elapsed/Math.max(.01,shot.end-shot.start)),enter=ease(elapsed/.32);
 const mode=shot.motion_scene;
 // The two alternatives receive equal emphasis, in sequence. Their identical
 // irrecoverable price remains visible throughout rather than following focus.
 const stayPulse=Math.sin(Math.PI*clamp((p-.04)/.44));
 const leavePulse=Math.sin(Math.PI*clamp((p-.52)/.44));
 const stayColor=p<.5?gold:white,leaveColor=p>=.5?gold:white;
 return <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position:'absolute',inset:0,pointerEvents:'none'}}>
  <defs><filter id="decisionObjectShadow" x="-35%" y="-35%" width="170%" height="170%">
   <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#000" floodOpacity="1"/>
   <feDropShadow dx="0" dy="0" stdDeviation="1.5" floodColor="#000" floodOpacity="1"/>
  </filter></defs>
  <g filter="url(#decisionObjectShadow)" opacity={enter} transform={`translate(0 ${18*(1-enter)})`}>
   {mode==='ticket_purchase'&&<Ticket scale={.94+.06*ease(elapsed/.5)}/>}
   {mode==='ticket_loss'&&<>
    <Ticket cross={ease((elapsed-.12)/.46)}/>
    <g opacity={ease((elapsed-.5)/.2)}><Label x={540} y={990} color={red}>sunk cost</Label></g>
   </>}
   {mode==='time_loss'&&<>
    <Clock progress={ease(p*.85)}/>
    <Label x={540} y={1010} color={gold}>1 hour</Label>
   </>}
   {mode==='future_choice'&&<>
    <Label x={540} y={515} color={gold}>next hour</Label>
    <Arrow d="M540 565 V625 M540 625 Q540 655 500 655 H320 V720 M300 700 L320 720 L340 700" color={stayColor} progress={ease(elapsed/.5)}/>
    <Arrow d="M540 625 Q540 655 580 655 H760 V720 M740 700 L760 720 L780 700" color={leaveColor} progress={ease((elapsed-.15)/.5)}/>
    <g opacity={ease((elapsed-.2)/.3)}>
     <g transform={`translate(320 840) scale(${1+.045*stayPulse}) translate(-320 -840)`}>
      <path d="M255 850 V785 Q255 760 280 760 H360 Q385 760 385 785 V850 M235 815 V895 H405 V815 M255 895 V925 M385 895 V925" stroke={stayColor} strokeWidth="9" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
     </g>
     <g transform={`translate(775 840) scale(${1+.045*leavePulse}) translate(-775 -840)`}>
      <path d="M700 925 V765 H810 V925 M700 765 L780 790 V925 M765 855 H766" stroke={leaveColor} strokeWidth="9" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <Arrow d="M805 850 H900 M880 830 L900 850 L880 870" color={leaveColor}/>
     </g>
     <Label x={320} y={975} size={52} color={stayColor}>stay</Label><Label x={775} y={975} size={52} color={leaveColor}>leave</Label>
     {[320,775].map(x=><g key={x}>
      <Label x={x} y={1065} size={61} color={red}>$20</Label>
      <path d={`M${x-69} 1082 L${x+69} 1047`} stroke={red} strokeWidth="7" strokeLinecap="round"/>
     </g>)}
    </g>
   </>}
   {mode==='decision_reset'&&<>
    <Ticket x={290} y={720} scale={.55} cross={1}/>
    <Label x={290} y={870} size={47} color={red}>gone</Label>
    <path d="M500 535 V1000" stroke={white} opacity=".6" strokeWidth="4" strokeDasharray="10 16"/>
    <Arrow d="M575 590 H900 M870 560 L900 590 L870 620" color={mint} progress={ease(elapsed/.5)}/>
    <Clock x={745} y={805} r={110} color={mint} progress={.12*ease(p)}/>
    <Label x={745} y={1010} size={52} color={mint}>next hour</Label>
   </>}
  </g>
 </svg>;
};
