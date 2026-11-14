import * as T from './three.module.js';

// Codex-authored reusable geometry and joint hierarchy. No provider calls.
export const cube=new T.BoxGeometry(1,1,1);
const mats=new Map<string,any>();
export function material(color:string){if(!mats.has(color))mats.set(color,new T.MeshLambertMaterial({color}));return mats.get(color)}
export function box(parent:any,x:number,y:number,z:number,w:number,h:number,d:number,color:any){
 const m=new T.Mesh(cube,typeof color==='string'?material(color):color);m.position.set(x,y,z);m.scale.set(w,h,d);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;
}
export function pixelMaterial(base:string,kind:string){
 const canvas=document.createElement('canvas');canvas.width=canvas.height=32;const c=canvas.getContext('2d')!;
 c.fillStyle=base;c.fillRect(0,0,32,32);
 for(let i=0;i<150;i++){const x=(i*17+3)%32,y=(i*29+Math.floor(i/9))%32;c.fillStyle=i%2?'#ffffff16':'#00000018';c.fillRect(x,y,kind==='wood'?9:2,kind==='wood'?1:2)}
 if(kind==='wood'){c.fillStyle='#36251245';for(let y=0;y<32;y+=8)c.fillRect(0,y,32,1)}
 const tex=new T.CanvasTexture(canvas);tex.magFilter=T.NearestFilter;tex.minFilter=T.NearestFilter;tex.colorSpace=T.SRGBColorSpace;
 return new T.MeshLambertMaterial({map:tex});
}
export function actor(shirt:string,skin:string,hair:string){
 const root=new T.Group();const torso=new T.Group();root.add(torso);
 box(torso,0,1.48,0,.78,.94,.42,shirt);
 const head=new T.Group();head.position.set(0,2.28,0);torso.add(head);
 box(head,0,0,0,.73,.72,.69,skin);box(head,0,.32,-.04,.77,.17,.74,hair);
 box(head,0,.1,-.32,.75,.5,.12,hair);box(head,-.31,.17,0,.13,.4,.65,hair);
 for(const x of [-.17,.17]){box(head,x,.015,.351,.16,.12,.025,'#fff5df');box(head,x+.025,.005,.369,.065,.09,.024,'#263743')}
 box(head,.015,-.13,.38,.14,.14,.12,skin);const mouth=box(head,0,-.25,.36,.23,.045,.025,'#7e4035');
 const arms=[];const elbows=[];const hands=[];const legs=[];const eyes=[];
 for(const x of [-.17,.17])eyes.push(box(head,x,.015,.385,.17,.12,.028,skin));
 for(const x of [-.58,.58]){
  const a=new T.Group();a.position.set(x,1.9,0);torso.add(a);box(a,0,-.22,0,.34,.44,.4,shirt);const elbow=new T.Group();elbow.position.y=-.44;a.add(elbow);box(elbow,0,-.2,0,.33,.4,.38,skin);const hand=new T.Group();hand.position.set(0,-.4,0);elbow.add(hand);arms.push(a);elbows.push(elbow);hands.push(hand);
 }
 for(const x of [-.22,.22]){const l=new T.Group();l.position.set(x,1.05,0);root.add(l);box(l,0,-.43,0,.36,.87,.41,'#344d69');box(l,0,-.94,.07,.39,.2,.57,'#26313b');legs.push(l)}
 return {root,torso,head,arms,elbows,hands,eyes,legs,mouth};
}
export function fish(){
 const root=new T.Group();box(root,0,0,0,.52,.2,.17,'#efad67');box(root,.02,.09,0,.36,.055,.18,'#dd6b50');
 box(root,-.32,0,0,.16,.3,.07,'#e66d4c');box(root,.22,.01,.09,.045,.06,.025,'#162d33');box(root,.22,.01,-.09,.045,.06,.025,'#162d33');return root;
}
export function line(a:any,b:any,color:string){const g=new T.BufferGeometry().setFromPoints([new T.Vector3(...a),new T.Vector3(...b)]);return new T.Line(g,new T.LineBasicMaterial({color}));}
export function beam(parent:any,a:any,b:any,width:number,color:string){const av=new T.Vector3(...a),bv=new T.Vector3(...b);const obj=box(parent,0,0,0,width,av.distanceTo(bv),width,color);obj.position.copy(av.add(bv).multiplyScalar(.5));obj.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),new T.Vector3(...b).sub(new T.Vector3(...a)).normalize());return obj}
export function crate(parent:any,x:number,z:number,wood:any){
 const g=new T.Group();g.position.set(x,.12,z);parent.add(g);
 box(g,0,.09,0,1,.18,.8,wood);for(const side of [-1,1]){box(g,side*.46,.38,0,.1,.6,.8,wood);box(g,0,.38,side*.36,1,.6,.1,wood)}
 return g;
}

