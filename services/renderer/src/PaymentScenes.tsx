import React from 'react';
import {useCurrentFrame} from 'remotion';
const clamp=(x:number)=>Math.min(1,Math.max(0,x));
const ease=(x:number)=>{x=clamp(x);return x*x*(3-2*x)};
const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
const ink='#f5f0e7',yellow='#ffe34d',purple='#bba1ff',coral='#ff787b';
const Label=({x,y,children,size=52,color=ink,opacity=1}:any)=><text x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontFamily="DejaVu Sans" fontWeight="700" fontSize={size} fill={color} opacity={opacity}>{children}</text>;
const Headphones=({x,y,scale=1,color=purple}:any)=><g transform={`translate(${x} ${y}) scale(${scale})`} fill="none" stroke={color} strokeWidth="18" strokeLinecap="round"><path d="M-85 45 V-10 A85 85 0 0 1 85-10 V45"/><rect x="-105" y="0" width="42" height="88" rx="17" fill="#171626"/><rect x="63" y="0" width="42" height="88" rx="17" fill="#171626"/></g>;
const Tile=({x,y,w=170,h=130,children,color=purple,opacity=1}:any)=><g opacity={opacity}><rect x={x-w/2} y={y-h/2} width={w} height={h} rx="20" fill="#171626" stroke={color} strokeWidth="3"/><Label x={x} y={y} size={w<130?32:48} color={color}>{children}</Label></g>;
// Every monetary quantity comes from the validated example. The LLM selects a
// visible operation, never writes a balance or replaces arithmetic with prose.
export const PaymentScene=({lesson,shot}:any)=>{
 const t=useCurrentFrame()/30,p=clamp((t-shot.start)/(shot.end-shot.start));
 const {unit_price:price,installments:n,purchases:q}=lesson.installment_example;
 const installment=price/n,total=price*q,due=installment*q;
 const mode=shot.motion_scene;
 const cols=Math.min(n,4),tileW=Math.min(170,720/cols),gap=tileW+22;
 const pos=(i:number)=>({x:540+(i%cols-(cols-1)/2)*gap,y:780+Math.floor(i/cols)*165});
 return <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{position:'absolute',inset:0}}>
 <defs><radialGradient id="payment-glow"><stop stopColor="#39324f" stopOpacity=".5"/><stop offset="1" stopColor="#08090e" stopOpacity="0"/></radialGradient></defs>
 <circle cx="540" cy="870" r="520" fill="url(#payment-glow)"/>
 {mode==='price_tag'&&<>
  <Headphones x={540} y={610} scale={1.7}/>
  <g transform={`translate(540 970) scale(${1+.08*Math.sin(Math.PI*clamp(p*4))})`}><Label x={0} y={0} size={164} color={yellow}>${installment}</Label></g>
  <Label x={540} y={1090} size={39}>per payment</Label>
  <g opacity={ease((p-.55)*4)}><path d="M360 1190 H720" stroke={purple} strokeWidth="3"/><Label x={540} y={1250} size={62}>${price} total</Label></g>
 </>}
 {mode==='split_payment'&&<>
  <Label x={540} y={440} size={104}>${price}</Label>
  <path d="M540 525 V600 M525 585 L540 605 L555 585" fill="none" stroke={purple} strokeWidth="6"/>
  {Array.from({length:n},(_,i)=>{const target=pos(i),a=ease((p-.08-i*.035)*2.6);return <Tile key={i} x={mix(540,target.x,a)} y={mix(610,target.y,a)} w={tileW} opacity={a}>${installment}</Tile>})}
  <Label x={540} y={1220} size={60} color={yellow}>{n} × ${installment} = ${price}</Label>
 </>}
 {mode==='stack_purchases'&&<>
  {Array.from({length:q},(_,i)=>{const a=ease((p-i*.14)*4);return <g key={i} opacity={a} transform={`translate(${(1-a)*250} 0)`}><Headphones x={260} y={480+i*180} scale={.65} color={[purple,yellow,coral][i%3]}/><Label x={540} y={515+i*180} size={80} color={[purple,yellow,coral][i%3]}>${installment}</Label><Label x={790} y={515+i*180} size={34}>× {n}</Label></g>})}
  <path d={`M180 ${535+q*180} H890`} stroke={ink} strokeWidth="3"/>
  <Label x={540} y={640+q*180} size={92} color={yellow} opacity={ease((p-.5)*3)}> ${due} now</Label>
 </>}
 {mode==='payment_calendar'&&<>
  {Array.from({length:n},(_,i)=>{const x=170+(i%4)*230,y=540+Math.floor(i/4)*360;return <g key={i} opacity={ease((p-i*.04)*4)}><rect x={x-88} y={y-85} width={176} height={250} rx="14" fill="#14121f" stroke={purple} strokeWidth="3"/><path d={`M${x-88} ${y-20} H${x+88}`} stroke={purple} strokeWidth="3"/><Label x={x} y={y-52} size={27}>{i===0?'NOW':`PAY ${i+1}`}</Label>{Array.from({length:q},(_,j)=><Label key={j} x={x} y={y+25+j*34} size={29} color={[purple,yellow,coral][j%3]}>${installment}</Label>)}<Label x={x} y={y+215} size={52} color={yellow}>${due}</Label></g>})}
  <Label x={540} y={1230} size={40}>same-day purchases</Label>
 </>}
 {mode==='total_cost'&&<>
  {Array.from({length:q},(_,i)=>{const angle=-Math.PI/2+i*2*Math.PI/q,a=ease((p-.15)*1.8),x=mix(540+290*Math.cos(angle),540,a),y=mix(790+260*Math.sin(angle),850,a);return <g key={i} opacity={1-ease((p-.22)*5)}><Headphones x={x} y={y-100} scale={.6}/><Label x={x} y={y+25} size={68}>${price}</Label></g>})}
  <Label x={540} y={840} size={168} color={yellow} opacity={ease((p-.42)*4)}> ${total}</Label>
  <Label x={540} y={1040} size={44} opacity={ease((p-.42)*4)}>total commitment</Label>
 </>}
 {mode==='choice_balance'&&<>
  <Label x={290} y={450} size={35}>now</Label><Label x={760} y={450} size={35}>later</Label>
  <rect x="190" y={1160-(600/n)*ease(p*3)} width="200" height={(600/n)*ease(p*3)} rx="12" fill={purple}/>
  <rect x="660" y={1160-(600*(n-1)/n)*ease((p-.15)*2)} width="200" height={(600*(n-1)/n)*ease((p-.15)*2)} rx="12" fill={yellow}/>
  <Label x={290} y={1220} size={66}>${due}</Label><Label x={760} y={1220} size={66} color={yellow}>${total-due}</Label>
  <path d="M140 1160 H920" stroke={ink} strokeWidth="3"/>
 </>}
 {mode==='receipt'&&<>
  <Headphones x={540} y={465} scale={1}/>
  <Label x={540} y={705} size={66}>{q} × ${price}</Label>
  <path d="M260 790 H820" stroke={purple} strokeWidth="3" strokeDasharray="8 12"/>
  <Label x={540} y={925} size={164} color={yellow}>${total}</Label>
  <Label x={540} y={1080} size={47}>{n} payments of ${due}</Label>
  <Label x={540} y={1200} size={32} color={purple}>no interest / fees assumed</Label>
 </>}
 </svg>;
};
