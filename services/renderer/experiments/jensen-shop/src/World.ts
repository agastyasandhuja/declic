import * as T from './three.module.js';
import {actor,box,beam} from './ModelKit';
import {state,ease,mix,armSolution} from './Story.mjs';
// Original procedural stylization; no scanned likeness, game asset or celebrity voice.
export function createShop(canvas:HTMLCanvasElement,lesson:any){
 const renderer=new T.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});
 renderer.setSize(1080,1920,false);renderer.setPixelRatio(1);renderer.setClearColor('#17272e');renderer.outputColorSpace=T.SRGBColorSpace;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;
 const scene=new T.Scene();scene.add(new T.HemisphereLight('#fff5dd','#536278',2.1));
 const key=new T.DirectionalLight('#ffe4b7',3.5);key.position.set(-3,9,5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);scene.add(key);
 const fill=new T.DirectionalLight('#bce3ff',1.2);fill.position.set(6,5,-2);scene.add(fill);
 const camera=new T.PerspectiveCamera(42,1080/1920,.1,80);
 const resources:any[]=[];
 const vector=(a:number[])=>new T.Vector3(...a);
 function textTexture(lines:string[],color='#253440',background='#f5edcf'){
  const c=document.createElement('canvas');c.width=1024;c.height=512;const ctx=c.getContext('2d')!;
  ctx.fillStyle=background;ctx.fillRect(0,0,1024,512);ctx.fillStyle=color;ctx.textAlign='center';ctx.textBaseline='middle';
  lines.forEach((line,i)=>{ctx.font=`bold ${lines.length>2?78:120}px DejaVu Sans`;ctx.fillText(line,512,(i+.5)*512/lines.length,960)});
  const texture=new T.CanvasTexture(c);texture.colorSpace=T.SRGBColorSpace;resources.push(texture);return texture;
 }
 function printed(parent:any,lines:string[],width:number,height:number,color='#253440',background='#f5edcf'){
  const material=new T.MeshBasicMaterial({map:textTexture(lines,color,background),side:T.DoubleSide});resources.push(material);
  const mesh=new T.Mesh(new T.PlaneGeometry(width,height),material);resources.push(mesh.geometry);parent.add(mesh);return mesh;
 }
 box(scene,0,-.16,0,8,.3,7,'#556267');
 for(let x=-4;x<4;x+=.8)box(scene,x,.001,0,.012,.008,7,'#68757b');
 box(scene,0,2,-2.4,8,4,.15,'#344955');
 // Shelves hold objects; the sold GPU is a single transferable mesh, never duplicated.
 const shelf=new T.Group();scene.add(shelf);box(shelf,-1.5,1.42,-.85,1.8,.14,.65,'#bb8f5b');
 for(const x of [-2.25,-.75])box(shelf,x,.74,-1.07,.10,1.42,.10,'#263943');
 box(shelf,-1.5,.56,-.85,1.8,.12,.65,'#a67f53');
 for(let i=0;i<3;i++)box(shelf,-2.0+i*.45,.78,-.88,.31,.34,.3,'#557f84');
 const shelfTag=printed(shelf,['$60'],.6,.27);shelfTag.position.set(-.9,1.3,-.51);
 const counter=new T.Group();scene.add(counter);box(counter,.35,.56,.0,3.25,1.12,.62,'#9f7350');box(counter,.35,1.17,0,3.45,.15,.8,'#d7bb8c');
 // The drawer receives cash once; it is not reduced merely because COGS is recorded.
 box(counter,.3,1.28,.12,.72,.11,.5,'#34474c');
 const ledgerRoot=new T.Group();ledgerRoot.position.set(1.25,1.30,.05);ledgerRoot.rotation.x=-Math.PI/2;scene.add(ledgerRoot);
 box(ledgerRoot,0,0,-.035,1.3,1.15,.07,'#334e6b');
 const coverPivot=new T.Group();ledgerRoot.add(coverPivot);coverPivot.position.set(-.64,0,.05);box(coverPivot,.64,0,0,1.28,1.13,.055,'#3c5976');
 let ledger:any=null,lastLedger='';
 function ledgerPage(first:boolean,second:boolean,profit:boolean){
  const key=[first,second,profit].join();if(key===lastLedger)return;lastLedger=key;
  if(ledger){ledgerRoot.remove(ledger);ledger.geometry.dispose();ledger.material.map.dispose();ledger.material.dispose()}
  const lines=profit?['Sales 100','COGS 60','Gross profit 40']:second?['Dr Cash 100','Cr Sales 100','Dr COGS 60','Cr Inventory 60']:first?['Dr Cash 100','Cr Sales 100']:['Dr             Cr'];
  ledger=printed(ledgerRoot,lines,1.21,1.06);ledger.position.z=.012;
 }
 function person(shirt:string,skin:string,hair:string,isJensen=false){
  const a=actor(shirt,skin,hair);scene.add(a.root);a.arms.forEach((arm:any)=>arm.visible=false);a.eyes.forEach((e:any)=>e.scale.y=.03);
  const joints=[-1,1].map(side=>{const upper=box(a.root,0,0,0,.28,.52,.30,shirt),lower=box(a.root,0,0,0,.25,.5,.27,shirt);const hand=new T.Group();a.root.add(hand);box(hand,0,0,0,.23,.18,.23,skin);return {side,upper,lower,hand}});
  if(isJensen){
   // Square eyeglass frames, swept gray hair, leather lapels and zipper.
   for(const x of [-.18,.18]){for(const y of [-.065,.095])box(a.head,x,y,.414,.31,.028,.028,'#101b20');for(const dx of [-.15,.15])box(a.head,x+dx,.015,.414,.028,.18,.028,'#101b20')}
   box(a.head,0,.025,.42,.08,.025,.03,'#101b20');
   for(let i=0;i<5;i++){const tuft=box(a.head,-.3+i*.14,.43+(i%2)*.015,-.05,.19,.18,.65,i%2?'#b7bbb9':'#d8dad5');tuft.rotation.z=-.12}
   box(a.head,.33,.17,0,.11,.36,.6,'#c4c8c6');
   const zip=box(a.torso,0,1.47,.23,.035,.88,.025,'#aaaeb0');
   for(const side of [-1,1]){const lapel=box(a.torso,side*.15,1.76,.255,.16,.35,.035,'#43494b');lapel.rotation.z=side*.35;box(a.torso,side*.23,1.35,.23,.18,.026,.03,'#a0a4a4')}
  }
  return {...a,joints};
 }
 const jensen=person('#202629','#d5a982','#c1c6c4',true),customer=person('#a95a43','#b78162','#3b302b'),keeper=person('#668e86','#e2b99a','#4e453e');
 function face(a:any,target:number[]){a.root.rotation.y=Math.atan2(target[0]-a.root.position.x,target[2]-a.root.position.z)}
 function limb(mesh:any,start:any,end:any,length:number){mesh.position.copy(start).add(end).multiplyScalar(.5);mesh.scale.y=length;mesh.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),end.clone().sub(start).normalize())}
 function reach(a:any,index:number,target:number[]){
  const j=a.joints[index],shoulder=[j.side*.58,1.9,0];a.root.updateMatrixWorld(true);
  const local=a.root.worldToLocal(vector(target));const solution=armSolution(shoulder,local.toArray(),j.side);
  const s=vector(shoulder),e=vector(solution.elbow),h=vector(solution.hand);
  limb(j.upper,s,e,.52);limb(j.lower,e,h,.5);j.hand.position.copy(h);a.root.updateMatrixWorld(true);return j.hand;
 }
 function resting(a:any,index:number){const x=a.joints[index].side*.63;return a.root.localToWorld(new T.Vector3(x,.98,.12)).toArray()}
 function gpuModel(){const g=new T.Group();box(g,0,0,0,.66,.12,.40,'#263638');box(g,0,-.06,.08,.5,.06,.25,'#3f755d');box(g,.1,-.05,.24,.35,.08,.08,'#bda363');
  for(const x of [-.17,.17]){const fan=new T.Mesh(new T.CylinderGeometry(.13,.13,.025,16),new T.MeshStandardMaterial({color:'#11191e',metalness:.3,roughness:.7}));fan.position.set(x,.08,0);g.add(fan);for(let k=0;k<6;k++){const blade=box(g,x,.10,0,.20,.018,.025,'#75878a');blade.rotation.y=k*Math.PI/3}}
  scene.add(g);return g;
 }
 const gpu=gpuModel(),cash=new T.Group();scene.add(cash);box(cash,0,0,0,.36,.03,.24,'#87b698');const banknote=printed(cash,['100'],.32,.20,'#2d5b45','#b8d4ae');banknote.rotation.x=-Math.PI/2;banknote.position.y=.021;
 const cost=new T.Group();scene.add(cost);box(cost,0,0,0,.38,.035,.25,'#ecdbb3');const costPrint=printed(cost,['60'],.34,.21);costPrint.rotation.x=-Math.PI/2;costPrint.position.y=.025;
 function attach(prop:any,hand:any){if(prop.parent!==hand)hand.add(prop);prop.position.set(0,.06,0);const q=new T.Quaternion();hand.getWorldQuaternion(q);prop.quaternion.copy(q.invert());}
 function place(prop:any,position:number[]){if(prop.parent!==scene)scene.add(prop);prop.position.fromArray(position);prop.quaternion.identity()}
 function openEyes(a:any,t:number,phase:number){const blink=(t+phase)%4.7;for(const eye of a.eyes)eye.scale.y=blink<.12?.12:.015}
 return {update(t:number){
  const s=state(lesson,t),{i,u}=s;jensen.root.position.fromArray(s.jensen);customer.root.position.fromArray(s.customer);keeper.root.position.fromArray(s.bookkeeper);
  face(jensen,i===0?[0,0,.75]:i===1?mix([0,0,.75],s.gpuShelf,u/.4):i===2?mix(s.gpuShelf,[0,0,.75],(u-.30)/.35):i===3?mix([0,0,.75],s.bookkeeper,u/.35):[0,0,.75]);
  face(customer,i===2&&u>.70?mix([0,0,-.65],[4,0,2],(u-.70)/.08):i>2?[4,0,2]:[0,0,-.65]);face(keeper,i===3?s.gpuShelf:[1.25,1.3,.05]);
  jensen.head.rotation.z=i===3?-.12*ease(u):i>=7?-.08*ease(u):0;keeper.head.rotation.z=i===3?.10:0;
  customer.legs[0].rotation.x=(i===1||i===2&&u>.76)?.22*Math.sin(u*14):0;customer.legs[1].rotation.x=-customer.legs[0].rotation.x;
  openEyes(jensen,t,0);openEyes(customer,t,1.8);openEyes(keeper,t,3.2);
  for(const a of [jensen,customer,keeper])a.root.updateMatrixWorld(true);
  let jGrip=resting(jensen,1);
  if(i===2){const shelfGrip=[s.gpuShelf[0],s.gpuShelf[1]-.06,s.gpuShelf[2]];jGrip=u<.30?mix(resting(jensen,1),shelfGrip,u/.30):u<.7?mix(shelfGrip,s.handoff,(u-.30)/.38):[.55,2.45,-.45]}
  if(i>2&&i<7)jGrip=[.55,2.45,-.45];if(i===7)jGrip=mix([.55,2.45,-.45],resting(jensen,1),u/.55);
  const jHand=reach(jensen,1,jGrip);reach(jensen,0,resting(jensen,0));
  let cGrip=resting(customer,0);
  if(i===2&&u<.18)cGrip=mix(resting(customer,0),[.3,1.30,.12],u/.18);
  else if(i===2&&u<.70)cGrip=mix([.3,1.30,.12],s.handoff,(u-.18)/.52);
  else if(i===2)cGrip=mix(s.handoff,[s.customer[0]+.3,1.45,s.customer[2]-.25],(u-.70)/.06);
  else if(i>2)cGrip=[s.customer[0]+.3,1.45,s.customer[2]-.25];
  const cHand=reach(customer,0,cGrip);reach(customer,1,resting(customer,1));
  const kGrip=i===3?mix(resting(keeper,0),[-.9,1.7,.05],ease(u/.5)):i===5?u<.8?mix([1.1,1.36,.08],[.7,1.36,.08],u/.8):mix([.7,1.36,.08],resting(keeper,0),(u-.8)/.2):i===4?mix([1.1,1.36,.08],resting(keeper,0),(u-.4)/.25):resting(keeper,0);
  const kHand=reach(keeper,0,kGrip);reach(keeper,1,resting(keeper,1));
  if(s.gpuOwner==='shelf')place(gpu,s.gpuShelf);else attach(gpu,s.gpuOwner==='jensen'?jHand:cHand);
  if(s.cashOwner==='drawer')place(cash,[.3,1.36,.12]);else attach(cash,cHand);
  cost.visible=i===5;if(cost.visible){if(u<.8)attach(cost,kHand);else place(cost,[.7,1.36,.08])}
  ledgerPage(s.firstEntry,s.secondEntry,s.profit);coverPivot.rotation.y=i<4?0:-Math.PI*.92*(i===4?ease(u/.35):1);
  // Camera cuts reveal mechanisms; no camera motion substitutes for a transfer.
  const close=i===4||i===5||i===6;
  const cameraPosition=close?[2.8,4.2,3.5]:i===1?[-3.6,3.2,3.8]:i===2?[-5.2,4.2,3.4]:i===3?[-4.8,4.2,5.2]:[-5.6,5.4,9.0];
  const target=close?[.85,1.1,0]:i===1?[-.8,1.4,-.6]:[.0,1.2,-.1];camera.position.fromArray(cameraPosition);camera.lookAt(...target);
  renderer.render(scene,camera);
 },dispose(){scene.traverse((o:any)=>{if(o.isMesh){o.geometry?.dispose();if(o.material?.map)o.material.map.dispose();o.material?.dispose()}});for(const r of resources)r.dispose();renderer.dispose()}};
}
