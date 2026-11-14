import React from 'react';
import {AbsoluteFill,Audio,staticFile,useCurrentFrame} from 'remotion';
const clamp=(n:number)=>Math.max(0,Math.min(1,n));
const smooth=(n:number)=>{n=clamp(n);return n*n*(3-2*n)};
const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
const purple='#bca1ff',gold='#f6d78e',white='#f5f3ee';
const Text=({x,y,children,size=88,color=white,opacity=1}:any)=><text x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize={size} fill={color} opacity={opacity}>{children}</text>;
const Brackets=({x,y,w,h}:any)=><path d={`M${x+20} ${y} H${x} V${y+h} H${x+20} M${x+w-20} ${y} H${x+w} V${y+h} H${x+w-20}`} fill="none" stroke={white} strokeWidth="4"/>;

// Minimal motion grammar: highlight → copy factors → products → sum → result cell.
// Narration, explanatory captions and credits belong outside this visual canvas.
export const MathLesson=({lesson}:{lesson:any})=>{
 const t=useCurrentFrame()/30,{a,b,cells}=lesson.math;
 const cell=cells.find((c:any)=>c.start<=t&&t<c.end),done=t>=cells.at(-1).end;
 const active=cell||cells[t<cells[0].start?0:cells.length-1];
 const p=cell?clamp((t-cell.start)/(cell.end-cell.start)):0;
 const rows=a.length,n=a[0].length,cols=b[0].length;
 const adx=n===3?110:155,bdx=cols===3?110:155,dy=150;
 const ax=70,bx=645,sy=570,aw=(n-1)*adx+125,bw=(cols-1)*bdx+125;
 const apos=(r:number,k:number)=>({x:ax+62.5+k*adx,y:sy+r*dy});
 const bpos=(k:number,c:number)=>({x:bx+62.5+c*bdx,y:sy+k*dy});
 const cdx=cols===3?140:175,cdy=145,cw=(cols-1)*cdx+150,ch=(rows-1)*cdy+150;
 const cx=540-cw/2,cy=rows===3?1240:1310;
 const cpos=(r:number,c:number)=>({x:cx+75+c*cdx,y:cy+75+r*cdy});
 const previous=cells[Math.max(0,cells.indexOf(active)-1)];
 const row=mix(previous.row,active.row,smooth(p/.10)),col=mix(previous.col,active.col,smooth(p/.10));
 const fly=smooth((p-.10)/.22),products=smooth((p-.55)/.06),sum=smooth((p-.74)/.05),land=smooth((p-.82)/.14);
 const target=cpos(active.row,active.col),spacing=n===3?315:420,startX=540-(n-1)*spacing/2;
 const sourceSize=n===3||cols===3?76:88;
 const resultSize=Math.max(...cells.map((c:any)=>String(c.result).length))>2?72:94;
 return <AbsoluteFill style={{background:'#030303',fontFamily:'DejaVu Serif,serif'}}>
 <svg viewBox="0 0 1080 1920" width="1080" height="1920">
  <text x="540" y="270" textAnchor="middle" fontSize="64" fill={white}><tspan fill={purple}>Matrix</tspan> multiplication</text>
  <Brackets x={ax} y={sy-78} w={aw} h={(rows-1)*dy+156}/>
  <Brackets x={bx} y={sy-78} w={bw} h={(b.length-1)*dy+156}/>
  <Text x={525} y={sy+(Math.max(rows,b.length)-1)*dy/2} size={70}>×</Text>
  {!done&&<>
   <rect x={ax+12} y={sy+row*dy-63} width={aw-24} height={126} rx={14} stroke={purple} strokeWidth={3} fill={purple} fillOpacity={.06}/>
   <rect x={bx+13+col*bdx} y={sy-65} width={99} height={(b.length-1)*dy+130} rx={14} stroke={gold} strokeWidth={3} fill={gold} fillOpacity={.055}/>
  </>}
  {a.flatMap((r:number[],i:number)=>r.map((v,k)=><Text key={`a${i}-${k}`} {...apos(i,k)} size={sourceSize} color={!done&&i===active.row?purple:white} opacity={done||i===active.row?1:.5}>{v}</Text>))}
  {b.flatMap((r:number[],i:number)=>r.map((v,k)=><Text key={`b${i}-${k}`} {...bpos(i,k)} size={sourceSize} color={!done&&k===active.col?gold:white} opacity={done||k===active.col?1:.5}>{v}</Text>))}
  {!cell&&<Text x={540} y={1050} size={80}>=</Text>}
  {cell&&<>
   {active.products.map((v:number,k:number)=>{const aa=apos(active.row,k),bb=bpos(k,active.col),x=startX+k*spacing,y=1050,d=n===3?65:80,size=n===3?62:76;
    return <g key={k}>
     <g opacity={(1-smooth((p-.49)/.05))*smooth((fly-.07)/.12)}>
      <Text x={mix(aa.x,x-d,fly)} y={mix(aa.y,y,fly)} size={size} color={purple}>{a[active.row][k]}</Text>
      <Text x={x} y={y} size={48} opacity={fly}>×</Text>
      <Text x={mix(bb.x,x+d,fly)} y={mix(bb.y,y,fly)} size={size} color={gold}>{b[k][active.col]}</Text>
      {k<n-1&&<Text x={x+spacing/2} y={y} size={50} opacity={fly}>+</Text>}
     </g>
     <g opacity={products*(1-smooth((p-.68)/.05))}>
      <Text x={x} y={y} size={78}>{v<0?`(${v})`:v}</Text>
      {k<n-1&&<Text x={x+spacing/2} y={y} size={50}>+</Text>}
     </g>
    </g>;
   })}
   <Text x={mix(540,target.x,land)} y={mix(1050,target.y,land)} size={mix(106,resultSize,land)} color={purple} opacity={sum*(1-smooth((p-.975)/.02))}>{active.result}</Text>
  </>}
  <Brackets x={cx} y={cy} w={cw} h={ch}/>
  {cells.map((c:any,i:number)=>{const q=cpos(c.row,c.col),complete=t>=c.end-.03;
   return <g key={i}>
    {cell===c&&<rect x={q.x-62} y={q.y-61} width={124} height={122} rx={13} stroke={purple} strokeWidth={2.5} fill={purple} fillOpacity={.05}/>}
    <Text {...q} size={resultSize} opacity={complete?1:cell===c?0:.35}>{complete?c.result:t<cells[0].start?'?':'·'}</Text>
   </g>;
  })}
  {done&&<path d={`M${cx} ${cy+ch+45} H${cx+cw}`} stroke={purple} strokeWidth={3} opacity={smooth((t-cells.at(-1).end)/.4)}/>}
 </svg>
 <Audio src={staticFile(lesson.audio_file)}/>
 </AbsoluteFill>;
};
