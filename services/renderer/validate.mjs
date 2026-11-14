import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function validatePack(root) {
 const real=fs.realpathSync(root);
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
 if(!Array.isArray(manifest.files)||manifest.files.length>80)throw Error('Invalid manifest');
 let total=0;
 for(const entry of manifest.files) {
  if(typeof entry.path!=='string'||path.isAbsolute(entry.path)||entry.path.split(/[\\/]/).includes('..'))throw Error('Invalid path');
  const file=path.join(root,entry.path);
  const resolved=fs.realpathSync(file);
  if(!resolved.startsWith(real+path.sep)||fs.lstatSync(file).isSymbolicLink())throw Error('Asset escape');
  const stat=fs.statSync(file);total+=stat.size;
  if(!stat.isFile()||stat.size!==entry.size||stat.size>500_000_000||total>800_000_000)throw Error('Invalid asset size');
  const hash=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  if(hash!==entry.sha256)throw Error('Asset digest mismatch');
 }
 const lesson=JSON.parse(fs.readFileSync(path.join(root,'lesson.json'),'utf8'));
 if(!['dialogue_gameplay','visual_explainer'].includes(lesson.format_id)||lesson.frame_count<900||lesson.frame_count>1800)throw Error('Invalid lesson');
 for(const asset of ['narration.wav',lesson.background,...Object.values(lesson.characters||{})].filter(Boolean)) {
  if(!/^[a-zA-Z0-9_-]+\.(wav|mp4|png|jpg)$/.test(asset)||!manifest.files.some(f=>f.path===`assets/${asset}`))throw Error('Unstaged asset');
 }
 if(lesson.custom_scene) {
  if(!manifest.files.some(f=>f.path==='scene.tsx'))throw Error('Missing scene');
  const source=fs.readFileSync(path.join(root,'scene.tsx'),'utf8');
  if(source.length>40000||/\b(eval|Function|fetch|XMLHttpRequest|WebSocket|require|process|globalThis|window|document|importScripts)\b|import\s*\(|https?:|file:|dangerouslySetInnerHTML/.test(source))throw Error('Forbidden scene capability');
  for(const m of source.matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g))if(!['react','remotion'].includes(m[1]))throw Error('Forbidden import');
 }
 return lesson;
}
