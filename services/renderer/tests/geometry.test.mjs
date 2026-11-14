import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {build} from 'esbuild';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
const area=points=>Math.abs(points.reduce((sum,p,i)=>{
 const q=points[(i+1)%points.length];return sum+p[0]*q[1]-p[1]*q[0];
},0))/2;
// Convex polygon clipping independently checks overlap in the actual SVG output.
const intersection=(subject,clip)=>{
 let result=subject;
 for(let i=0;i<clip.length;i++) {
  const a=clip[i],b=clip[(i+1)%clip.length],input=result;result=[];
  if(!input.length)break;
  for(let j=0;j<input.length;j++) {
   const p=input[j],q=input[(j+1)%input.length],dp=cross(a,b,p),dq=cross(a,b,q);
   const pin=dp>=-1e-7,qin=dq>=-1e-7;
   if(pin)result.push(p);
   if(pin!==qin) {
    const f=dp/(dp-dq);result.push([p[0]+f*(q[0]-p[0]),p[1]+f*(q[1]-p[1])]);
   }
  }
 }
 return result;
};
const square=(x,y,s)=>[[x,y],[x+s,y],[x+s,y+s],[x,y+s]];

test('rendered geometric endpoints preserve four congruent nonoverlapping triangles at bounded aspect ratios',async t=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'geometry-render-test-'));
 t.after(async()=>{delete globalThis.__geometryTestFrame;await fs.rm(dir,{recursive:true,force:true})});
 const renderer=fileURLToPath(new URL('../',import.meta.url)),outfile=path.join(dir,'geometry.mjs');
 await build({entryPoints:[path.join(renderer,'src/PythagoreanLesson.tsx')],bundle:true,platform:'node',format:'esm',outfile,
  plugins:[{name:'frame-only-remotion',setup(builder){
   builder.onResolve({filter:/^remotion$/},()=>({path:'remotion',namespace:'test'}));
   builder.onLoad({filter:/.*/,namespace:'test'},()=>({resolveDir:renderer,contents:
    "import React from 'react'; export const AbsoluteFill=({children})=>React.createElement('div',null,children); export const Audio=()=>null; export const staticFile=v=>v; export const useCurrentFrame=()=>globalThis.__geometryTestFrame;"}));
  }}]});
 const {PythagoreanLesson}=await import(pathToFileURL(outfile).href);
 for(const [a,b] of [[3,4],[2,5],[1,9],[9,1],[1,1],[9,9]]) {
  const A=780*a/(a+b),B=780*b/(a+b);
  for(const second of [8,15]) {
   globalThis.__geometryTestFrame=second*30;
   const svg=renderToStaticMarkup(React.createElement(PythagoreanLesson,{lesson:{math:{a,b,c_squared:a*a+b*b},audio_file:'fixture.wav'}}));
   const matches=[...svg.matchAll(/<g opacity="([^"]+)" transform="translate\(([-\d.]+) ([-\d.]+)\) rotate\((\d+)\) scale\(([-\d.]+)\)"><path d="M0 0 L([-\d.]+) 0 L0 ([-\d.]+) Z"/g)];
   assert.equal(matches.length,4,'The authored scene must contain four rigid triangles');
   const triangles=matches.map(m=>{
    const [opacity,x,y,degrees,scale,width,height]=m.slice(1).map(Number),angle=degrees*Math.PI/180;
    assert.equal(opacity,1);assert.equal(scale,1);
    return [[0,0],[width,0],[0,height]].map(([px,py])=>[x+px*Math.cos(angle)-py*Math.sin(angle),y+px*Math.sin(angle)+py*Math.cos(angle)]);
   });
   for(const [i,triangle] of triangles.entries()) {
    assert.ok(Math.abs(area(triangle)-A*B/2)<1e-6,'Triangle area changed');
    for(const point of triangle)assert.ok(point.every(v=>v>=-1e-7&&v<=780+1e-7),'Triangle escapes enclosing square');
    for(const other of triangles.slice(i+1))assert.ok(area(intersection(triangle,other))<1e-6,'Endpoint triangles overlap');
   }
   const gaps=second===8?[[[A,0],[780,A],[B,780],[0,B]]]:[square(0,0,A),square(A,A,B)];
   for(const gap of gaps)for(const triangle of triangles)assert.ok(area(intersection(gap,triangle))<1e-6,'Claimed square overlaps a triangle');
   assert.ok(Math.abs(gaps.reduce((sum,g)=>sum+area(g),0)+triangles.reduce((sum,g)=>sum+area(g),0)-780**2)<1e-6,'Endpoint does not tile enclosing square');
  }
 }
});
