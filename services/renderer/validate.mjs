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
 if(!['dialogue_gameplay','visual_explainer','space_explainer','math_explainer'].includes(lesson.format_id)||!Number.isInteger(lesson.frame_count)||lesson.frame_count<(lesson.format_id==='math_explainer'?600:900)||lesson.frame_count>1800)throw Error('Invalid lesson');
 if(lesson.presentation!==undefined&&!['guided_v1','reference_v2','reference_v3'].includes(lesson.presentation))throw Error('Invalid presentation');
 if(lesson.background_mode!==undefined&&!['concept_only','gameplay'].includes(lesson.background_mode))throw Error('Invalid background mode');
 if(lesson.teaching_beats!==undefined&&!['reference_v2','reference_v3'].includes(lesson.presentation)) {
  const kinds=['hook','prediction','reveal','retrieval','feedback'];
  if(!Array.isArray(lesson.teaching_beats)||lesson.teaching_beats.length!==5)throw Error('Invalid teaching beats');
  let previousEnd=0;
  for(const [i,b] of lesson.teaching_beats.entries()) {
   if(b.kind!==kinds[i]||typeof b.text!=='string'||!b.text.trim()||b.text.length>72||b.text.trim().split(/\s+/).length>12
      ||![b.start,b.speech_end,b.end].every(Number.isFinite)||b.start<previousEnd
      ||b.speech_end<=b.start||b.end<b.speech_end||b.end>lesson.frame_count/30
      ||(i===0&&b.start!==0))throw Error('Invalid teaching beat timing/text');
   const pause=b.kind==='prediction'?2:b.kind==='retrieval'?3:0;
   if(Math.abs(b.end-b.speech_end-pause)>0.001)throw Error('Invalid thinking pause');
   previousEnd=b.end;
  }
 }
 if(['reference_v2','reference_v3'].includes(lesson.presentation)&&lesson.format_id!=='math_explainer') {
  if(lesson.custom_scene)throw Error('Reference scenes use the authored cinematic renderer');
  if(lesson.teaching_beats?.length)throw Error('Reference scenes cannot contain teaching cards');
  if(!Array.isArray(lesson.shots)||lesson.shots.length<6||lesson.shots.length>16)throw Error('Invalid shots');
  if(!['none','linked_list_reverse'].includes(lesson.trace_kind))throw Error('Invalid trace kind');
  if(!Array.isArray(lesson.segments)||lesson.segments.length!==lesson.shots.length)throw Error('Invalid shot segments');
  let end=0;
  for(const [i,s] of lesson.shots.entries()) {
   if(!['image','diagram','kinetic','space'].includes(s.kind)||!['push','pull','pan_left','pan_right','orbit','drift'].includes(s.camera)
     ||!['starfield','galaxy','cosmic_web','cosmic_sheet','cosmic_overview','filament_detail','solar_system','nebula','light_travel','lookback','scale_ladder','gravity'].includes(s.space_mode)
     ||![s.start,s.end].every(Number.isFinite)||s.start!==end||s.end<=s.start||s.end>lesson.frame_count/30
     ||s.segment_id!==lesson.segments[i].id||s.start!==lesson.segments[i].start
     ||typeof s.headline!=='string'||s.headline.length>52||!Array.isArray(s.labels)||s.labels.length>5
     ||s.labels.some(l=>typeof l!=='string'||l.length>24)||!Array.isArray(s.asset_ids)||s.asset_ids.length>2
     ||s.asset_ids.some(id=>!Object.hasOwn(lesson.images||{},id))
     ||(s.kind==='image'&&!s.asset_ids.length)||(s.kind==='space'&&lesson.format_id!=='space_explainer'))throw Error('Invalid shot timeline/content');
   if(s.diagram_demo!==undefined&&!['trace','broken_first_link'].includes(s.diagram_demo))throw Error('Invalid diagram demonstration');
   end=s.end;
  }
  if(Math.abs(end-lesson.frame_count/30)>.001)throw Error('Incomplete shot timeline');
  if(Object.keys(lesson.images||{}).length>6)throw Error('Too many images');
  for(const image of Object.values(lesson.images||{})) {
   if(typeof image.file!=='string'||!image.file.endsWith('.jpg'))throw Error('Invalid normalized image');
   for(const [id,f] of Object.entries(image.framing||{})) {
    if(!lesson.shots.some(s=>s.shot_id===id)||!['cover','contain'].includes(f.fit)
     ||![f.focus_x,f.focus_y].every(v=>Number.isFinite(v)&&v>=0&&v<=1)
     ||![f.zoom_start,f.zoom_end].every(v=>Number.isFinite(v)&&v>=1&&v<=1.35))throw Error('Invalid image framing');
   }
  }
 }
 for(const asset of [lesson.audio_file||'narration.wav',lesson.background,...Object.values(lesson.characters||{}),...Object.values(lesson.images||{}).map(i=>i.file)].filter(Boolean)) {
  if(!/^[a-zA-Z0-9_-]+\.(wav|mp4|png|jpg)$/.test(asset)||!manifest.files.some(f=>f.path===`assets/${asset}`))throw Error('Unstaged asset');
 }
 if(lesson.review_frames!==undefined&&(!Array.isArray(lesson.review_frames)||lesson.review_frames.length>40||lesson.review_frames.some(f=>!Number.isInteger(f)||f<0||f>=lesson.frame_count)))throw Error('Invalid review frames');
 if(lesson.format_id==='math_explainer') {
  const {a,b,cells}=lesson.math||{};
  const valid=m=>Array.isArray(m)&&m.length>=2&&m.length<=3&&m.every(r=>Array.isArray(r)&&r.length>=2&&r.length<=3&&r.length===m[0].length&&r.every(v=>Number.isInteger(v)&&Math.abs(v)<=9));
  if(!valid(a)||!valid(b)||a[0].length!==b.length||!Array.isArray(cells)||cells.length!==a.length*b[0].length||lesson.custom_scene||lesson.presentation!=='reference_v3')throw Error('Invalid math plan');
  let end=lesson.minimal_math?1.5:6;
  for(const [i,cell] of cells.entries()) {
   const row=Math.floor(i/b[0].length),col=i%b[0].length;
   const products=a[row].map((v,k)=>v*b[k][col]);
   if(cell.row!==row||cell.col!==col||JSON.stringify(cell.products)!==JSON.stringify(products)||cell.result!==products.reduce((x,y)=>x+y,0)||cell.start!==end||!Number.isFinite(cell.end)||cell.end-cell.start<4||cell.end-cell.start>8)throw Error('Invalid math arithmetic/timing');
   end=cell.end;
  }
  if(end>lesson.frame_count/30-(lesson.minimal_math?1.5:2))throw Error('Incomplete math payoff');
 }
 if(lesson.custom_scene) {
  if(!manifest.files.some(f=>f.path==='scene.tsx'))throw Error('Missing scene');
  const source=fs.readFileSync(path.join(root,'scene.tsx'),'utf8');
  if(source.length>40000||/\b(eval|Function|fetch|XMLHttpRequest|WebSocket|require|process|globalThis|window|document|importScripts)\b|import\s*\(|https?:|file:|dangerouslySetInnerHTML/.test(source))throw Error('Forbidden scene capability');
  for(const m of source.matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g))if(!['react','remotion'].includes(m[1]))throw Error('Forbidden import');
 }
 return lesson;
}
