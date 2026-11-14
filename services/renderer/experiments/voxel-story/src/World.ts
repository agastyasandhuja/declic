import {cube,box,pixelMaterial,actor,fish,line,beam,crate} from './ModelKit';
import * as T from './three.module.js';
import {facing,turn,spots,waterTargets,walkToSpot,eventsFor,posePhase} from './Blocking.mjs';

// All models/textures are original procedural geometry. No game files or remote assets.
const clamp=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(v:number)=>{const q=clamp(v);return q*q*(3-2*q)};
const lerp=(a:number,b:number,p:number)=>a+(b-a)*p;
export function createWorld(canvas:HTMLCanvasElement){
 const renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:false,preserveDrawingBuffer:true});
 renderer.setSize(720,1280,false);renderer.setPixelRatio(1);renderer.setClearColor('#8dc6ef');
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.outputColorSpace=T.SRGBColorSpace;
 const scene=new T.Scene();scene.background=new T.Color('#8dc6ef');scene.fog=new T.Fog('#8dc6ef',32,75);
 const camera=new T.PerspectiveCamera(46,720/1280,.1,120);
 scene.add(new T.HemisphereLight('#e6f5ff','#61714d',2.1));const sun=new T.DirectionalLight('#fff0ce',2.6);sun.position.set(-8,15,8);sun.castShadow=true;
 sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-15,right:15,top:15,bottom:-15,near:.5,far:50});sun.shadow.bias=-.0005;scene.add(sun);
 const grass=pixelMaterial('#78a84e','grass'),dirt=pixelMaterial('#8a6a42','dirt'),wood=pixelMaterial('#ad7b49','wood'),roof=pixelMaterial('#73553c','wood'),sand=pixelMaterial('#cfbd88','sand');
 box(scene,0,-1.5,0,80,1,80,dirt);
 // Four solid banks leave a genuine recessed lake, not an image of water.
 box(scene,-15,-.35,0,20,1,40,grass);box(scene,15,-.35,0,20,1,40,grass);
 box(scene,0,-.35,-14,10,1,21,grass);box(scene,0,-.35,14,10,1,21,grass);
 box(scene,0,-1.08,0,10,.2,7,sand);
 const water=box(scene,0,-.27,0,9.9,.04,6.9,new T.MeshPhongMaterial({color:'#2ea4b0',transparent:true,opacity:.35,shininess:90,depthWrite:false}));water.castShadow=false;
 // Chunky shoreline and a dock with individual slats.
 for(let i=0;i<10;i++){box(scene,-4.5+i,-.02,3.65,.98,.32,.55,sand);box(scene,-4.5+i,-.02,-3.65,.98,.32,.55,sand)}
 for(let i=0;i<9;i++)box(scene,0,.24,3+i*.36,2.5,.16,.34,wood);
 for(const x of [-1.04,1.04])for(const z of [3.2,5.6])box(scene,x,-.05,z,.2,.9,.2,roof);
 // Houses, tree canopies and clouds create parallax in every camera angle.
 const house=(x:number,z:number,scale:number)=>{const g=new T.Group();g.position.set(x,0,z);g.scale.setScalar(scale);scene.add(g);
  box(g,0,1.3,0,3,2.6,2.7,wood);for(let i=0;i<4;i++)box(g,0,2.7+i*.25,0,3.8-i*.65,.3,3.2,roof);
  box(g,.6,.85,1.37,.7,1.7,.06,'#493b30');box(g,-.7,1.55,1.38,.8,.7,.07,'#b9e5ed');box(g,-.7,1.55,1.43,.06,.7,.03,'#71553c');
  for(const a of [-1.43,1.43])box(g,a,1.25,1.38,.16,2.5,.15,roof);
 };
 house(-6.5,9,1.15);house(6,11,1.1);
 house(-5.9,-6.7,1.3);house(.2,-8,1.1);house(6.2,-6.8,1.25);
 for(let i=0;i<14;i++){const x=i%2?-9-i*.65:9+i*.65,z=-3-Math.floor(i/2)*3;box(scene,x,1.6,z,.55,3.2,.55,roof);box(scene,x,3.4,z,2.4,1.9,2.5,grass);box(scene,x+.35,4.5,z,1.8,1.1,1.9,grass)}
 for(let i=0;i<10;i++){const g=new T.Group();g.position.set(-25+i*6,12+(i%3),-18-i%2*7);box(g,0,0,0,4,.6,1.7,'#ffffff');box(g,-.8,.4,0,2.3,.5,1.6,'#ffffff');scene.add(g)}
 for(let i=0;i<26;i++){const x=(i%2?-1:1)*(5.8+(i*7%13)*.4),z=-3+(i*11%21)*.52;box(scene,x,.2,z,.08,.5,.08,'#497239');if(i%4===0)box(scene,x,.49,z,.25,.15,.25,i%3?'#f7de65':'#df8d81')}
 const colors=['#ec934c','#668fc4','#9f78a3','#8bbd7d','#d0b25c','#5eb7b1','#d97f7f'];
 const actors=colors.map((c,i)=>{const a=actor(c,i%2?'#bd8965':'#e0ae85',i%3?'#554033':'#34312e');scene.add(a.root);return a});
 const rods=actors.map(()=>{const g=new T.Group();scene.add(g);const shaft=beam(g,[0,0,0],[0,1,0],.065,'#62422c');const cord=line([0,0,0],[0,0,0],'#e6eee3');g.add(cord);g.userData={shaft,cord};return g});
 const crates=spots.map(([x,z])=>crate(scene,x+1.05,z+.25,wood));
 const stock=Array.from({length:24},()=>{const f=fish();scene.add(f);return f});
 const catches=spots.map(()=>Array.from({length:5},()=>{const f=fish();scene.add(f);return f}));
 const boot=new T.Group();box(boot,0,0,0,.32,.42,.25,'#544537');box(boot,.13,-.19,.02,.56,.2,.32,'#483c32');scene.add(boot);
 const ripple=Array.from({length:10},()=>{const r=new T.Mesh(new T.RingGeometry(.14,.18,12),new T.MeshBasicMaterial({color:'#d4fbef',transparent:true,opacity:.7,side:T.DoubleSide,depthWrite:false}));r.rotation.x=-Math.PI/2;r.position.y=-.23;scene.add(r);return r});
 const board=new T.Group();scene.add(board);board.position.set(2.5,0,4.3);box(board,0,1.7,0,1.6,1.05,.16,'#31544a');box(board,-.6,.7,0,.12,1.4,.15,wood);box(board,.6,.7,0,.12,1.4,.15,wood);
 for(const x of [-.4,.4]){const f=fish();f.position.set(x,1.7,.18);f.scale.setScalar(.85);board.add(f)}
 const monitor=actor('#eee4c8','#bf8a62','#4f4436');scene.add(monitor.root);monitor.root.position.set(2.5,.2,5.2);
 const sunset=new T.Mesh(new T.BoxGeometry(2,2,.2),new T.MeshBasicMaterial({color:'#fff3b6'}));sunset.position.set(-12,10,-20);scene.add(sunset);

 const splash=Array.from({length:28},()=>{const drop=box(scene,0,0,0,.065,.065,.065,'#d0f7ee');drop.castShadow=false;return drop});
 const hooked=actors.map(()=>{const f=fish();scene.add(f);return f});
 const floats=actors.map(()=>box(scene,0,0,0,.1,.15,.1,'#f6df9d'));
 const hands=actors.map(()=>new T.Vector3()),tips=actors.map(()=>new T.Vector3());
 const faceEvidence:any[]=[];
 function update(beat:any,u:number,t:number){
  const p=ease(u),s=beat.scene,events=eventsFor(s);
  const crowded=['rush','deplete','empty','commons','cost','rules','restore'].includes(s);
  const empty=['hook','empty','commons','cost'].includes(s),ruled=['rules','restore'].includes(s);
  const baseCount=empty?2:s==='access'?24:s==='subtract'?23:s==='extra'?22:20;
  const current=actors.map((_,i)=>events.find((e:any)=>e.actor===i&&u>=e.start&&u<e.end));
  board.visible=ruled;monitor.root.visible=ruled;
  monitor.root.rotation.y=facing([2.5,5.2],[0,4.2]);
  monitor.arms[0].rotation.x=-.7;monitor.arms[1].rotation.x=-.4;
  monitor.arms[0].rotation.z=s==='rules'?-1.1*ease(u/.2)*(1-ease((u-.55)/.2)):0;
  monitor.head.rotation.x=s==='rules'?.12*Math.sin(u*Math.PI*3):0;
  const day=s==='rules'?Math.sin(u*Math.PI)*.65:0;sun.intensity=2.6-day;
  scene.background.set(day>.4?'#edb69a':'#8dc6ef');sunset.position.y=10-day*9;
  faceEvidence.length=0;
  for(let i=0;i<actors.length;i++){
   const a=actors[i],[x,z]=spots[i],target=waterTargets[i];
   const event=current[i],q=event?clamp((u-event.start)/(event.end-event.start)):0,phase=posePhase(q);
   const walking=s==='rush'&&i>0?walkToSpot(i,u):null;
   const baseYaw=facing([x,z],target),crateYaw=facing([x,z],[x+1.05,z+.25]);
   let yaw=walking?walking.yaw:turn(baseYaw,crateYaw,phase.turnToCrate);
   if(['cost','rules'].includes(s))yaw=turn(baseYaw,facing([x,z],[2.5,5.2]),ease(u/.3));
   if(s==='commons'&&i>0)yaw=turn(baseYaw,facing([x,z],[0,4.2]),.65);
   const pos=walking?.position||[x,z];
   a.root.visible=i===0||crowded||(s==='subtract'&&i===1);
   a.root.position.set(pos[0],.2,pos[1]);a.root.rotation.y=yaw;
   const walkingNow=walking?.moving;const step=Math.sin(t*10+i*.7);
   a.legs[0].rotation.x=walkingNow?step*.48:0;a.legs[1].rotation.x=-a.legs[0].rotation.x;
   a.torso.position.y=walkingNow?Math.abs(step)*.035:Math.sin(t*1.8+i)*.012;
   a.torso.rotation.set(event?.045*phase.lift:0,0,event?-.04*phase.lift:0);
   a.head.rotation.set(empty?.18:phase.lift?-.1*phase.lift:.08,Math.sin(t*.7+i)*.05,0);
   // Blink, deliberate head turn, breathing; no uniform waving across the crowd.
   const blink=(t+i*.73)%3.7;
   a.eyes.forEach((eye:any)=>{eye.visible=blink<.1});
   a.mouth.scale.y=empty?.07:.045;
   a.arms[0].rotation.set(event?-.65+.9*phase.wind-.4*phase.lift:-.7,0,0);
   a.elbows[0].rotation.x=event?-.35-.2*phase.lift:-.3;
   a.arms[1].rotation.set(event?-.55-.3*phase.lift:-.4,0,0);
   a.elbows[1].rotation.x=event?-.5+.15*Math.sin(q*30):-.25;
   if(walkingNow){a.arms[0].rotation.x=-step*.35;a.arms[1].rotation.x=step*.35;a.elbows.forEach((e:any)=>e.rotation.x=-.2)}
   if(empty){const shrug=Math.sin(Math.PI*ease((u-.25)/.65));a.arms[1].rotation.z=-.55*shrug;a.head.rotation.z=.09*shrug}
   if(s==='rules'){a.arms[0].rotation.x=-.25;a.elbows[0].rotation.x=-.2;a.head.rotation.x=.1*Math.sin(u*Math.PI*4+i)*Math.sin(u*Math.PI)}
   a.root.updateMatrixWorld(true);a.hands[0].getWorldPosition(hands[i]);
   const hand=hands[i],dir=new T.Vector3(Math.sin(yaw),0,Math.cos(yaw));
   const reach=event?lerp(.8,2.1,phase.cast)*(1-phase.lift*.55):1.4;
   tips[i].copy(hand).addScaledVector(dir,reach);tips[i].y+=event?1.1+phase.wind*.7+phase.lift*.6:1.4;
   const rod=rods[i],shaft=rod.userData.shaft;rod.position.set(0,0,0);
   shaft.position.copy(hand).add(tips[i]).multiplyScalar(.5);
   shaft.scale.set(.065,hand.distanceTo(tips[i]),.065);
   shaft.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),tips[i].clone().sub(hand).normalize());
   rod.visible=a.root.visible&&!['cost','rules'].includes(s)&&!walkingNow;
   const attr=rod.userData.cord.geometry.attributes.position;
   attr.setXYZ(0,tips[i].x,tips[i].y,tips[i].z);attr.setXYZ(1,target[0],-.2,target[1]);attr.needsUpdate=true;
   floats[i].visible=rod.visible;floats[i].position.set(target[0],-.18+Math.sin(t*5+i)*.025,target[1]);
   crates[i].visible=a.root.visible;
   let n=s==='subtract'&&i===0?1:s==='extra'&&i===0?2:s==='rush'&&i===0?4:s==='deplete'&&i===0?4:['commons','cost'].includes(s)&&i===0?4:ruled?2:0;
   n+=events.filter((e:any)=>e.actor===i&&u>=e.end).length;
   for(let j=0;j<5;j++){const f=catches[i][j];f.visible=a.root.visible&&j<Math.min(n,5);f.position.set(x+1.05+(j%2-.5)*.22,.55+Math.floor(j/2)*.12,z+.25);f.rotation.set(0,j*.7,0)}
   hooked[i].visible=false;
   // Semantic evidence uses world forward and target vectors, not camera-facing heuristics.
   faceEvidence.push({actor:i,visible:a.root.visible,walking:!!walkingNow,deposit:phase.turnToCrate,
    forward:[Math.sin(yaw),Math.cos(yaw)],target:[target[0]-pos[0],target[1]-pos[1]],
    hand:[hand.x,hand.y,hand.z],rodBase:[hand.x,hand.y,hand.z]});
  }
  for(let i=0;i<stock.length;i++){
   const f=stock[i],ev=events.find((e:any)=>e.fish===i);
   let count=baseCount;if(ruled)count=s==='rules'?Math.round(2+10*ease((u-.5)*2)):Math.round(12+8*p);
   f.visible=i<count&&!(ev&&u>=ev.start+(ev.end-ev.start)*.42);
   const angle=t*.35+i*2.4,x=Math.sin(angle)*3.6,z=Math.cos(angle*.76+i)*2.6;
   f.position.set(x,-.63+Math.sin(t*3+i)*.08,z);
   f.rotation.set(0,Math.atan2(-.76*Math.sin(angle*.76+i)*2.6,Math.cos(angle)*3.6),Math.sin(t*7+i)*.04);
  }
  for(let k=0;k<actors.length;k++){
   const ev=current[k];if(!ev)continue;const q=clamp((u-ev.start)/(ev.end-ev.start)),phase=posePhase(q);
   const fish=hooked[k],target=waterTargets[k],hand=hands[k],attr=rods[k].userData.cord.geometry.attributes.position;
   const bob=floats[k];
   if(q<.33){const c=ease((q-.13)/.2);bob.position.set(lerp(hand.x,target[0],c),lerp(hand.y,-.18,c)+Math.sin(c*Math.PI)*.8,lerp(hand.z,target[1],c));attr.setXYZ(1,bob.position.x,bob.position.y,bob.position.z)}
   if(q>=.42){
    fish.visible=true;bob.visible=false;const lift=ease((q-.42)/.34);
    fish.position.set(lerp(target[0],hand.x,lift),lerp(-.5,hand.y+.15,lift)+Math.sin(lift*Math.PI)*.6,lerp(target[1],hand.z,lift));
    if(q>.76){const drop=ease((q-.76)/.24),[x,z]=spots[k];fish.position.set(lerp(hand.x,x+1.05,drop),lerp(hand.y,.6,drop)+Math.sin(drop*Math.PI)*.2,lerp(hand.z,z+.25,drop));}
    fish.rotation.set(Math.sin(t*24)*.12,t*3,Math.sin(t*18)*.15);
    attr.setXYZ(1,fish.position.x,fish.position.y,fish.position.z);
   }
   attr.needsUpdate=true;
  }
  boot.visible=s==='hook'||s==='empty';
  const forward=new T.Vector3(Math.sin(actors[0].root.rotation.y),0,Math.cos(actors[0].root.rotation.y));
  boot.position.copy(hands[0]).addScaledVector(forward,.65);boot.position.y+=.2+Math.sin(t*3)*.04;boot.rotation.z=Math.sin(t*2)*.12;
  if(boot.visible){const a=rods[0].userData.cord.geometry.attributes.position;a.setXYZ(1,boot.position.x,boot.position.y+.2,boot.position.z);a.needsUpdate=true;floats[0].visible=false}
  for(let i=0;i<ripple.length;i++){const r=ripple[i];r.visible=!empty;const q=(t*.6+i*.17)%1;r.position.x=Math.sin(i*5.4)*3.5;r.position.z=Math.cos(i*3.5)*2.5;r.scale.setScalar(.5+q*2);r.material.opacity=(1-q)*.45;}
  for(let j=0;j<splash.length;j++){
   const k=Math.floor(j/4),ev=current[k],drop=splash[j];drop.visible=false;if(!ev)continue;
   const q=(u-ev.start)/(ev.end-ev.start),age=(q-.33)*1.8;
   if(age>=0&&age<.4){const [x,z]=waterTargets[k],a=j*2.4;drop.visible=true;drop.position.set(x+Math.cos(a)*age*.7,-.2+1.8*age-4.5*age*age,z+Math.sin(a)*age*.7)}
  }
  if(s==='restore'){
   const f=hooked[0],q=ease((u-.15)/.5),hand=hands[0],target=waterTargets[0];f.visible=u>.1&&u<.67;rods[0].visible=false;floats[0].visible=false;
   f.position.set(lerp(hand.x,target[0],q),lerp(hand.y,-.6,q)+Math.sin(q*Math.PI)*.35,lerp(hand.z,target[1],q));f.rotation.set(0,t*2,.1*Math.sin(t*15));
  }
  camera.position.set(...beat.camera[0].map((v:number,i:number)=>lerp(v,beat.camera[1][i],p)));camera.lookAt(...beat.target);
  renderer.render(scene,camera);
 }
 return {update,evidence:()=>faceEvidence,dispose:()=>{scene.traverse((o:any)=>{if(o.geometry&&o.geometry!==cube)o.geometry.dispose()});renderer.dispose()}};
}
