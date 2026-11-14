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
