import * as T from './three.module.js';
import {actor, box, beam} from './ModelKit';
const ease=(x:number)=>{const v=Math.max(0,Math.min(1,x));return v*v*(3-2*v)};
const colors=['#efaa65','#83c4bb','#b79be1','#edd477','#82a5dc','#d68f97','#adc27a','#e6bca7','#77b6c8'];
export function createWorld(canvas:HTMLCanvasElement, overlay:HTMLCanvasElement){
 const renderer=new T.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});
 renderer.setSize(1080,1920,false);renderer.setPixelRatio(1);renderer.setClearColor('#122133');
 renderer.outputColorSpace=T.SRGBColorSpace;
 const scene=new T.Scene();scene.add(new T.HemisphereLight('#e2f1ff','#5c5463',2.2));
 const sun=new T.DirectionalLight('#ffe6c7',3);sun.position.set(-5,14,7);scene.add(sun);
 const camera=new T.PerspectiveCamera(42,1080/1920,.1,100);camera.position.set(0,20,23);camera.lookAt(0,0,0);
 box(scene,0,-.25,0,14,.4,15,'#22374a');
 const grid=new T.GridHelper(14,14,'#476276','#2b4457');grid.position.y=-.02;scene.add(grid);
 let group:any=null,previous:any=null,objects:any[]=[],edges:any[]=[];
 const materials:any[]=[],geometries:any[]=[],textures:any[]=[];
 const labels=overlay.getContext('2d')!;
 function drawLabels(){
  labels.clearRect(0,0,1080,1920);labels.font='bold 42px DejaVu Sans';
  const occupied:any[]=[];
  const overlap=(a:any,b:any)=>a.x<b.x+b.w+10&&a.x+a.w+10>b.x&&a.y<b.y+b.h+10&&a.y+a.h+10>b.y;
  const entries=objects.map(({root,node}:any)=>{
   const point=root.position.clone();point.y=node.glyph==='person'?2.1:.9;point.project(camera);
   const words=node.label.split(' ').filter(Boolean),lines:string[]=[];
   for(const word of words){const last=lines.length-1;if(last>=0&&(lines[last]+' '+word).length<=14)lines[last]+=' '+word;else lines.push(word)}
   if(node.value)lines.push(node.value);return {node,lines,x:(point.x+1)*540,y:(1-point.y)*960};
  }).filter(e=>e.lines.length).sort((a,b)=>a.y-b.y||a.x-b.x);
  for(const entry of entries){
   const w=Math.min(330,Math.max(...entry.lines.map(line=>labels.measureText(line).width))+30),h=entry.lines.length*49+18;
   const rect={x:Math.max(35,Math.min(1045-w,entry.x-w/2)),y:Math.max(200,entry.y-h-38),w,h};
   for(let tries=0;tries<10&&occupied.some(old=>overlap(rect,old));tries++){
    rect.y-=h+12;if(rect.y<200)rect.y=Math.min(1330-h,entry.y+70+tries*22);
   }
   occupied.push(rect);
   labels.strokeStyle='#aac5d5';labels.lineWidth=2;labels.beginPath();labels.moveTo(entry.x,entry.y-8);labels.lineTo(rect.x+rect.w/2,rect.y+rect.h);labels.stroke();
   labels.fillStyle='#172c3ff0';labels.fillRect(rect.x,rect.y,rect.w,rect.h);
   labels.fillStyle='#fff6e7';labels.textAlign='center';labels.textBaseline='middle';
   entry.lines.forEach((line,index)=>labels.fillText(line,rect.x+rect.w/2,rect.y+9+(index+.5)*49,rect.w-20));
  }
 }
 const pos=(n:any,p:number)=>new T.Vector3((n.x+((n.to_x??n.x)-n.x)*p-.5)*11,0,(n.y+((n.to_y??n.y)-n.y)*p-.5)*11);
 function rebuild(spec:any){
  if(group)scene.remove(group);group=new T.Group();scene.add(group);objects=[];edges=[];
  for(const [i,n]of spec.nodes.entries()){
   const root=new T.Group();group.add(root);let person:any=null;
   if(n.glyph==='person'){person=actor(colors[i%colors.length],'#dca97c','#423b39');root.add(person.root);person.root.scale.setScalar(.72)}
   else if(n.glyph==='coin'){
    const geo=new T.CylinderGeometry(.58,.58,.2,24);geometries.push(geo);const mat=new T.MeshStandardMaterial({color:'#efc65d',metalness:.4,roughness:.4});materials.push(mat);const mesh=new T.Mesh(geo,mat);mesh.position.y=.18;root.add(mesh);
   }else if(n.glyph==='circle'){
    const geo=new T.SphereGeometry(.55,20,14);geometries.push(geo);const mat=new T.MeshLambertMaterial({color:colors[i%colors.length]});materials.push(mat);const mesh=new T.Mesh(geo,mat);mesh.position.y=.57;root.add(mesh);
   }else{box(root,0,.43,0,1.15,.85,.8,colors[i%colors.length]);if(n.glyph==='crate'){for(const x of [-.48,.48])box(root,x,.45,.42,.08,.82,.08,'#745b45');box(root,0,.44,.43,1.1,.08,.08,'#745b45')}if(n.glyph==='book')box(root,.05,.43,.43,.95,.7,.05,'#f2e7cb')}

   objects.push({root,person,node:n});
  }
  for(const edge of spec.edges){const line=beam(group,[0,.12,0],[0,.12,1],.075,'#b7d8dc');edges.push({line,source:spec.nodes.findIndex((n:any)=>n.id===edge.source),target:spec.nodes.findIndex((n:any)=>n.id===edge.target)})}
 }
 return {update(spec:any,u:number,t:number){if(previous!==spec){rebuild(spec);previous=spec}const p=ease((u-.15)/.62);
  for(const {root,person,node}of objects){root.position.copy(pos(node,p));if(person){const target=objects.find(o=>o.node.id!==node.id);const end=target?pos(target.node,p):new T.Vector3(0,0,0);const dx=end.x-root.position.x,dz=end.z-root.position.z;root.rotation.y=Math.atan2(dx,dz);const moving=Math.abs((node.to_x??node.x)-node.x)+Math.abs((node.to_y??node.y)-node.y)>.01&&u>.15&&u<.77;person.legs[0].rotation.x=moving?.3*Math.sin(p*18):0;person.legs[1].rotation.x=-person.legs[0].rotation.x;person.arms[1].rotation.x=-.25-Math.sin(Math.PI*p)*.45;person.elbows[1].rotation.x=-.25;person.head.rotation.y=.06*Math.sin(t*1.5);person.mouth.scale.y=1+.3*Math.sin(t*13)}}
  for(const e of edges){const a=objects[e.source].root.position.clone();a.y=.12;const b=objects[e.target].root.position.clone();b.y=.12;e.line.position.copy(a.clone().add(b).multiplyScalar(.5));e.line.scale.y=a.distanceTo(b);e.line.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),b.sub(a).normalize())}
  camera.position.x=.6*Math.sin(t*.1);camera.lookAt(0,0,0);renderer.render(scene,camera);drawLabels();
 },dispose(){for(const x of [...materials,...geometries,...textures])x.dispose();renderer.dispose()}};
}
