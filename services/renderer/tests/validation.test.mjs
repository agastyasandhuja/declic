import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {validatePack} from '../validate.mjs';

const pack=(t)=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'lesson-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.mkdirSync(path.join(root,'assets'));
 fs.writeFileSync(path.join(root,'assets/narration.wav'),'fixture');
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify({format_id:'visual_explainer',frame_count:1200}));
 const manifest=()=>fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify({files:['assets/narration.wav','lesson.json',...(fs.existsSync(path.join(root,'scene.tsx'))?['scene.tsx']:[])].map(p=>({path:p,size:fs.statSync(path.join(root,p)).size,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')}))}));
 manifest();return {root,manifest};
};
test('valid staged pack and tampered media',t=>{const {root}=pack(t);assert.equal(validatePack(root).frame_count,1200);fs.appendFileSync(path.join(root,'assets/narration.wav'),'tamper');assert.throws(()=>validatePack(root),/size|digest/)});
test('path traversal and symlink rejection',t=>{const {root}=pack(t);fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify({files:[{path:'../escape'}]}));assert.throws(()=>validatePack(root),/path/)});
for(const source of ["import fs from 'node:fs'; export default ()=>null;","export default ()=>fetch('https://example.com');","import x from 'some-package'; export default ()=>null;"]){
 test('reject forbidden source '+source.slice(0,25),t=>{const {root,manifest}=pack(t);fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify({format_id:'visual_explainer',frame_count:1200,custom_scene:true}));fs.writeFileSync(path.join(root,'scene.tsx'),source);manifest();assert.throws(()=>validatePack(root),/Forbidden/)});
}
test('ordinary node property is valid scene data',t=>{
 const {root,manifest}=pack(t);
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify({format_id:'visual_explainer',frame_count:1200,custom_scene:true}));
 fs.writeFileSync(path.join(root,'scene.tsx'),"import React from 'react'; export default function Scene(){const state={node:0}; return <div>{state.node}</div>;}");
 manifest();assert.equal(validatePack(root).custom_scene,true);
});
test('manifest rejects symlink assets',t=>{
 const {root,manifest}=pack(t);fs.unlinkSync(path.join(root,'assets/narration.wav'));
 fs.symlinkSync('/etc/hosts',path.join(root,'assets/narration.wav'));manifest();
 assert.throws(()=>validatePack(root),/escape|link|path|file/i);
});

const teachingLesson=()=>({format_id:'visual_explainer',frame_count:1350,background_mode:'concept_only',teaching_beats:[
 {kind:'hook',text:'Can one link lose the whole list?',start:0,speech_end:3,end:3},
 {kind:'prediction',text:'Can you still reach node two?',start:3,speech_end:7,end:9},
 {kind:'reveal',text:'Save the next node.',start:9,speech_end:14,end:14},
 {kind:'retrieval',text:'What must you save?',start:35,speech_end:38,end:41},
 {kind:'feedback',text:'The original next node.',start:41,speech_end:44,end:44},
]});
test('accept measured teaching beats with bounded thinking pauses',t=>{
 const {root,manifest}=pack(t);
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(teachingLesson()));manifest();
 assert.equal(validatePack(root).teaching_beats[3].end,41);
});
for(const failure of ['overlap','missing_pause','out_of_range','long_text','wrong_order','nonfinite']) {
 test('reject malformed teaching pack: '+failure,t=>{
  const {root,manifest}=pack(t),lesson=teachingLesson();
  if(failure==='overlap')lesson.teaching_beats[2].start=8;
  if(failure==='missing_pause')lesson.teaching_beats[1].end=7;
  if(failure==='out_of_range')lesson.teaching_beats[4].end=50;
  if(failure==='long_text')lesson.teaching_beats[0].text='x'.repeat(73);
  if(failure==='wrong_order')lesson.teaching_beats[2].kind='feedback';
  if(failure==='nonfinite')lesson.teaching_beats[0].start=NaN;
  fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
  assert.throws(()=>validatePack(root),/teaching|pause/);
 });
}

const referenceLesson=()=>({format_id:'space_explainer',presentation:'reference_v2',frame_count:1200,trace_kind:'none',teaching_beats:[],images:{},
 segments:Array.from({length:6},(_,i)=>({id:`s${i}`,start:i*6,end:(i+1)*6})),
 shots:Array.from({length:6},(_,i)=>({segment_id:`s${i}`,kind:'space',camera:'push',space_mode:'galaxy',headline:'',labels:[],asset_ids:[],start:i*6,end:i===5?40:(i+1)*6}))});
test('reference space pack uses a continuous timeline without artificial pauses',t=>{
 const {root,manifest}=pack(t);fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(referenceLesson()));manifest();
 assert.equal(validatePack(root).shots.length,6);
});
for(const failure of ['missing_image','timeline_gap','nan','unbounded_text','unknown_mode','custom_scene']) {
 test('reject malformed reference scene: '+failure,t=>{
  const {root,manifest}=pack(t),lesson=referenceLesson();
  if(failure==='missing_image')lesson.shots[0].asset_ids=['not_staged'];
  if(failure==='timeline_gap')lesson.shots[1].start+=1;
  if(failure==='nan')lesson.shots[0].end=NaN;
  if(failure==='unbounded_text')lesson.shots[0].headline='x'.repeat(100);
  if(failure==='unknown_mode')lesson.shots[0].space_mode='arbitrary_code';
  if(failure==='custom_scene')lesson.custom_scene=true;
  fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
  assert.throws(()=>validatePack(root),/shot|Reference/);
 });
}
test('reject unbounded image framing even with a valid scene timeline',t=>{
 const {root,manifest}=pack(t),lesson=referenceLesson();
 lesson.shots[0].shot_id='first';
 lesson.images={image:{file:'image.jpg',framing:{first:{fit:'cover',focus_x:2,focus_y:.5,zoom_start:1,zoom_end:1.2}}}};
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
 assert.throws(()=>validatePack(root),/framing/);
});

const mathLesson=()=>({format_id:'math_explainer',presentation:'reference_v3',frame_count:1020,custom_scene:false,
 math:{a:[[1,3],[5,7]],b:[[2,4],[6,8]],cells:[
  {row:0,col:0,products:[2,18],result:20,start:6,end:12},
  {row:0,col:1,products:[4,24],result:28,start:12,end:18},
  {row:1,col:0,products:[10,42],result:52,start:18,end:24},
  {row:1,col:1,products:[20,56],result:76,start:24,end:30}]}});
test('math renderer independently verifies dot products and rejects tampered sums',t=>{
 const {root,manifest}=pack(t),lesson=mathLesson();
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
 assert.equal(validatePack(root).math.cells[0].result,20);
 lesson.math.cells[0].result=2;
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
 assert.throws(()=>validatePack(root),/arithmetic/);
});
for(const failure of ['shape','products','timeline','unsafe_samples'])test('reject malformed math '+failure,t=>{
 const {root,manifest}=pack(t),lesson=mathLesson();
 if(failure==='shape')lesson.math.a[0].push(2);
 if(failure==='products')lesson.math.cells[0].products=[1,19];
 if(failure==='timeline')lesson.math.cells[1].start=13;
 if(failure==='unsafe_samples')lesson.review_frames=[1000000];
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
 assert.throws(()=>validatePack(root),/math|review/);
});

test('minimal math accepts a 21-second timeline but spoken clips still require 30 seconds',t=>{
 const {root,manifest}=pack(t),lesson=mathLesson();
 lesson.minimal_math=true;lesson.frame_count=630;
 lesson.math.cells.forEach((c,i)=>{c.start=1.5+i*4.5;c.end=c.start+4.5});
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
 assert.equal(validatePack(root).frame_count,630);
 lesson.format_id='visual_explainer';
 fs.writeFileSync(path.join(root,'lesson.json'),JSON.stringify(lesson));manifest();
 assert.throws(()=>validatePack(root),/Invalid lesson/);
});
