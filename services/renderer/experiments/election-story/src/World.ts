import * as T from './three.module.js';
import {actor,box,pixelMaterial,cube} from './ModelKit';
import {states,ease,mix,yaw,clamp} from './ElectionMath.mjs';
const orange='#e99343',teal='#38a99e',cream='#f4e8cf';

export function createWorld(canvas:HTMLCanvasElement){
 const renderer=new T.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});
 renderer.setSize(720,1280,false);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;
 const scene=new T.Scene();scene.background=new T.Color('#a9d5e4');scene.fog=new T.Fog('#a9d5e4',35,75);
 const camera=new T.PerspectiveCamera(43,720/1280,.1,120);
 scene.add(new T.HemisphereLight('#f7f6e6','#63785a',2.2));
 const sun=new T.DirectionalLight('#fff0cf',2.4);sun.position.set(-7,15,10);sun.castShadow=true;
 sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-16,right:16,top:16,bottom:-16,near:.5,far:50});sun.shadow.bias=-.0005;scene.add(sun);
 const stone=pixelMaterial('#c8c9b4','stone'),grass=pixelMaterial('#80a974','grass'),wood=pixelMaterial('#ab8760','wood');
 box(scene,0,-.32,0,70,.5,70,grass);box(scene,0,-.02,1,16,.15,19,stone);
 for(let x=-8;x<9;x+=2)for(let z=-8;z<12;z+=2)box(scene,x,.07,z,1.95,.02,1.95,x%4?'#c5c8b7':'#d3d3c1');
 // Original civic hall. The example isn't a geographic U.S. map.
 box(scene,0,2.5,-9,13,5,4,cream);box(scene,0,5.2,-9,14,.4,4.7,'#ddd4be');
 for(let i=0;i<4;i++)box(scene,0,5.5+i*.25,-9,10-i*2.2,.26,4.2,cream);
 for(const x of [-5,-3,3,5]){box(scene,x,2.4,-6.7,.45,4.8,.5,'#fff6df');box(scene,x,4.8,-6.7,.75,.25,.75,'#e8dfc8')}
 box(scene,0,1.4,-6.95,2,2.8,.08,'#547a7e');
 for(const x of [-11,11])for(let z=-8;z<9;z+=5){box(scene,x,1.4,z,.5,2.8,.5,wood);box(scene,x,3,z,2.5,2.4,2.5,grass);box(scene,x+.3,4.1,z,1.7,.7,1.8,grass)}
 const toy=new T.Group();scene.add(toy);
 const regions=states.map((s:any)=>{
  const g=new T.Group();toy.add(g);g.position.set(s.x,0,s.z);
  const plate=box(g,0,.2,0,3.3,.34,3.7,'#e9ddbb');box(g,0,.4,-.8,1.45,.18,1,wood);
  for(const x of [-.59,.59])box(g,x,1.25,-1.13,.1,1.6,.1,wood);
  box(g,0,2.14,-1.13,1.7,.18,.8,'#567b85');box(g,0,1,-.85,.85,.8,.6,'#e9e8d8');box(g,0,1.405,-.85,.5,.015,.08,'#334c58');
  const tokens=Array.from({length:5},(_,i)=>box(g,(i-2)*.47,.62,.85,.35,.38,.35,'#f3c16e'));
  const person=actor('#7f95a2','#c48c68','#3f3533');g.add(person.root);person.root.scale.setScalar(.53);person.root.position.set(.25,.42,.25);person.root.rotation.y=Math.PI;
  return {g,plate,tokens,person};
 });
 const orangeActor=actor(orange,'#d6a17b','#403432'),tealActor=actor(teal,'#9e7158','#343236');
 const leads=[orangeActor,tealActor];leads.forEach((a,i)=>{scene.add(a.root);a.root.position.set(i?1.3:-1.3,.12,5.5)});
 const ballotStage=new T.Group();scene.add(ballotStage);
 const voter=actor('#7b8fc1','#d4a07e','#514139');ballotStage.add(voter.root);voter.root.position.set(0,.1,1.45);voter.root.rotation.y=Math.PI;
 box(ballotStage,.58,.71,.7,1,1.32,.85,cream);box(ballotStage,.58,1.38,.7,.6,.02,.075,'#314b59');
 const paper=box(ballotStage,0,0,0,.3,.025,.2,'#fffaf0');const mark=box(paper,0,.55,0,.5,.2,.35,teal);
 // Tallies use actual individual blocks, transferred once from each state.
 const receivers=[new T.Group(),new T.Group()];receivers.forEach((g,i)=>{scene.add(g);g.position.set(i?2.15:-2.15,.15,4.2);box(g,0,.1,0,1.8,.15,1.8,wood)});
 const transfers=states.map((s:any)=>Array.from({length:5},(_,j)=>box(scene,0,0,0,.35,.38,.35,s.teal>s.orange?teal:orange)));
 const confetti=Array.from({length:42},(_,i)=>box(scene,0,0,0,.12,.025,.08,i%2?orange:'#ffe7a2'));
 const allocation=new T.Group();scene.add(allocation);
 const columns=Array.from({length:5},(_,i)=>box(allocation,(i-2)*.75,.5,0,.5,1,.5,i<3?teal:'#e9bc61'));
 const crowd=Array.from({length:8},(_,i)=>{const a=actor(i%2?orange:teal,i%3?'#d7a27d':'#9d7058','#473a33');scene.add(a.root);a.root.scale.setScalar(.75);return a});
 const hp=new T.Vector3();
 function resetActor(a:any,i:number,t:number){
  a.torso.rotation.set(0,0,0);a.torso.position.y=Math.sin(t*1.7+i)*.008;
  a.head.rotation.set(0,0,0);a.arms.forEach((v:any)=>v.rotation.set(0,0,0));a.elbows.forEach((v:any)=>v.rotation.set(-.12,0,0));a.legs.forEach((v:any)=>v.rotation.set(0,0,0));
  a.eyes.forEach((v:any)=>v.visible=(t+i*.81)%4<.09);
 }
 function update(beat:any,u:number,t:number){
  const s=beat.scene,p=ease(u),isToy=['toy','narrow','landslide','certify'].includes(s);
  toy.visible=isToy;ballotStage.visible=s==='ballot';allocation.visible=s==='allocation';
  receivers.forEach(g=>g.visible=['narrow','landslide','electoral'].includes(s));
  columns.forEach((c,i)=>c.scale.y=mix(.05,1,ease((u-i*.09)/.35)));
  allocation.position.set(0,.2,1);allocation.scale.setScalar(1.8);
  leads.forEach((a,i)=>{
   resetActor(a,i,t);a.root.visible=!['ballot','allocation'].includes(s);a.root.position.set(i?1.3:-1.3,.12,5.5);a.root.rotation.y=0;
   if(['hook','electoral','outro','popular'].includes(s)){
    const reaction=ease((u-.2)/.45);
    const celebrate=(s==='hook'&&i===0)?(1-reaction):s==='electoral'&&i===1?reaction:0;
    a.arms[0].rotation.z=-1.65*celebrate;a.arms[1].rotation.z=1.65*celebrate;
    a.elbows[0].rotation.x=-.5*celebrate;a.elbows[1].rotation.x=-.5*celebrate;
    if(s==='hook'&&i===0){a.head.rotation.y=.65*reaction;a.head.rotation.z=-.12*reaction;a.arms[1].rotation.z=-.35*reaction}
    if(s==='outro'){a.head.rotation.y=(i?-.4:.4)*p;a.arms[0].rotation.z=.25*Math.sin(p*Math.PI);a.elbows[0].rotation.x=-.5*Math.sin(p*Math.PI)}
    if(s==='popular'&&i===0){a.arms[1].rotation.z=-.6*Math.sin(p*Math.PI);a.head.rotation.z=-.07}
   }else{
    a.root.rotation.y=yaw([i?1.3:-1.3,5.5],[0,0]);a.head.rotation.y=i?-.15:.15;
    a.arms[0].rotation.x=-.45*Math.sin(u*Math.PI);a.elbows[0].rotation.x=-.35;
   }
  });
  resetActor(voter,3,t);const reach=ease((u-.12)/.34),release=.55;
  voter.arms[0].rotation.x=mix(-.4,-1,reach);voter.elbows[0].rotation.x=-.2;
  voter.head.rotation.x=.18;voter.root.updateMatrixWorld(true);voter.hands[0].getWorldPosition(hp);
  paper.visible=u<.79;paper.position.copy(hp);paper.rotation.set(0,0,0);
  if(u>=release){const d=ease((u-release)/.23);paper.position.set(.58,mix(1.605,1.13,d),.7);paper.scale.y=mix(.025,.01,d)}else paper.scale.y=.025;
  if(u>.8){voter.arms[0].rotation.x=mix(-1,-.15,ease((u-.8)/.2));voter.head.rotation.x=mix(.18,0,ease((u-.8)/.2))}
  regions.forEach((r,i)=>{
   r.g.scale.setScalar(s==='toy'?mix(.01,1,ease((u-i*.1)/.5)):1);
   resetActor(r.person,i,t);r.person.arms[0].rotation.x=-.6;r.person.elbows[0].rotation.x=-.5;
   const awarded=s==='landslide'||s==='electoral'||(s==='narrow'&&i<2);
   const q=s==='electoral'?1:s==='landslide'&&i<2?1:ease((u-.25-i*.07)/.5);
   r.tokens.forEach((token:any,j:number)=>token.visible=!(awarded&&q>j*.07));
   transfers[i].forEach((token:any,j:number)=>{
    token.visible=awarded&&q>j*.07;
    const a=ease((q-j*.07)/.65),isTeal=i<2;
    const from=[states[i].x+(j-2)*.47,.62,states[i].z+.85];
    const index=isTeal?i*5+j:j;
    const to=[(isTeal?2.15:-2.15)+(index%3-1)*.45,.45+Math.floor(index/3)*.4,4.2];
    token.position.set(mix(from[0],to[0],a),mix(from[1],to[1],a)+Math.sin(a*Math.PI)*1.5,mix(from[2],to[2],a));
    token.rotation.set(0,a*Math.PI*2,0);
   });
  });
  crowd.forEach((a,i)=>{
   resetActor(a,i+4,t);a.root.visible=['hook','landslide','popular','outro'].includes(s);
   a.root.position.set(-5+i*.72,.12,2.8-(i%2)*.85);a.root.rotation.y=yaw([a.root.position.x,a.root.position.z],[-1.3,5.5]);
   const wave=Math.sin(clamp((u-i*.05)/.7)*Math.PI);a.arms[i%2].rotation.z=(i%2?-1:1)*(.35+.65*wave);a.elbows[i%2].rotation.x=-.5;
  });
  confetti.forEach((c,i)=>{
   const active=s==='hook'||s==='electoral',age=(u-.1)*3.4-i*.008;
   c.visible=active&&age>=0&&age<2.1;const x=s==='hook'?-1.3:1.3;
   c.position.set(x+Math.sin(i*4.7)*age*1.2,Math.max(.14,2.4+2.2*age-2.7*age*age),5.5+Math.cos(i*2.2)*age);
   c.rotation.set(age*4+i,age*3,age*5);
  });
  camera.position.set(...beat.camera[0].map((v:number,i:number)=>mix(v,beat.camera[1][i],p)));camera.lookAt(...beat.target);
  renderer.render(scene,camera);
 }
 return {update,dispose:()=>{scene.traverse((o:any)=>{if(o.geometry&&o.geometry!==cube)o.geometry.dispose()});renderer.dispose()}};
}
