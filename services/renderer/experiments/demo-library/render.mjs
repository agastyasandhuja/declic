import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {bundle} from '@remotion/bundler';
import {openBrowser,renderMedia,renderStill,selectComposition} from '@remotion/renderer';
const mode=process.env.DEMO_MODE;if(!['stills','video'].includes(mode))throw Error('Invalid mode');
const id=process.env.DEMO_ID;if(!/^[a-zA-Z0-9_-]{1,100}$/.test(id))throw Error('Invalid ID');
const source='/opt/renderer/demo';
const hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(hash('/vendor/three.module.js')!=='ce1fa418de16a19495a9f72495580e3015d7745c296d3ce0485897f902ddedfb')throw Error('Unexpected Three.js bytes');
fs.cpSync(source+'/src','/tmp/src',{recursive:true});
fs.copyFileSync('/vendor/three.module.js','/tmp/src/three.module.js');
fs.copyFileSync('/opt/renderer/PopCaptions.tsx','/tmp/src/PopCaptions.tsx');
fs.copyFileSync('/opt/renderer/ModelKit.ts','/tmp/src/ModelKit.ts');
const pack=path.join('/job',id),lesson=JSON.parse(fs.readFileSync(pack+'/lesson.json','utf8'));
const manifest=JSON.parse(fs.readFileSync(pack+'/manifest.json','utf8'));
for(const [file,expected]of Object.entries(manifest.files)){
 if(file.startsWith('/')||file.split('/').includes('..')||!/^([a-zA-Z0-9_.-]+\/)?[a-zA-Z0-9_.-]+$/.test(file)||hash(path.join(pack,file))!==expected)throw Error('Pack digest mismatch');
}
if(lesson.id!==id||!['dialogue','graphic','math','cartoon','three_d','timeline'].includes(lesson.format_style)||!Number.isInteger(lesson.frames)||lesson.frames<900||lesson.frames>1800||lesson.segments.length<6||lesson.segments.length>10)throw Error('Invalid lesson');
for(const [i,s]of lesson.segments.entries()){
 if(s.audio!==`speech-${i}.wav`||!Number.isFinite(s.start)||s.start<0||!Number.isFinite(s.end)||s.end<=s.start||s.end>lesson.frames/30||s.scene.nodes.length>9||s.scene.edges.length>12||!fs.existsSync(pack+'/assets/'+s.audio))throw Error('Invalid timing or asset');
 for(const n of s.scene.nodes)if(![n.x,n.y,n.to_x??n.x,n.to_y??n.y].every(v=>Number.isFinite(v)&&v>=.05&&v<=.95)||n.label.length>24||n.value.length>16)throw Error('Invalid scene node');
}
for(const [role,file]of Object.entries(lesson.characters))if(!['peter','stewie'].includes(role)||!['peter.png','stewie-standing-v2.png'].includes(file))throw Error('Invalid character asset');
if(lesson.words.length>400||!lesson.words.every(w=>typeof w.text==='string'&&w.text.length<=100&&Number.isFinite(w.start)&&w.start>=0&&w.end>=w.start&&w.end<=lesson.frames/30))throw Error('Invalid word timestamps');
const serveUrl=await bundle({entryPoint:'/tmp/src/Root.tsx',publicDir:'/job',outDir:'/tmp/bundle',webpackOverride:c=>({...c,cache:false,resolve:{...c.resolve,modules:['/opt/renderer/node_modules','node_modules']}})});
const browser=await openBrowser('chrome',{browserExecutable:'/usr/bin/chromium',chromiumOptions:{gl:'swangle'}});
try{
 const common={serveUrl,inputProps:{lesson},browserExecutable:'/usr/bin/chromium',puppeteerInstance:browser,chromiumOptions:{gl:'swangle'},timeoutInMilliseconds:90000,mediaCacheSizeInBytes:64*1024*1024};
 const composition=await selectComposition({...common,id:'DemoLesson'});
 const output='/output';fs.mkdirSync(output,{recursive:true});
 if(mode==='stills'){
  const frames=[...new Set(lesson.segments.flatMap(s=>[.05,.5,.95].map(p=>Math.min(lesson.frames-1,Math.round((s.start+(s.end-s.start)*p)*30)))))];
  const index=[];for(const [i,frame]of frames.entries()){const file=`frame-${String(i).padStart(2,'0')}.png`;await renderStill({...common,composition,frame,scale:.5,output:path.join(output,file)});index.push({file,frame,time:frame/30})}
  fs.writeFileSync(path.join(output,'frame-index.json'),JSON.stringify(index));
 }else{
  let last=-1;await renderMedia({...common,composition,codec:'h264',audioCodec:'aac',pixelFormat:'yuv420p',sampleRate:48000,crf:22,concurrency:2,outputLocation:path.join(output,'lesson.mp4'),
   onProgress:({progress})=>{const p=Math.floor(progress*10)*10;if(p!==last){last=p;console.log(`${id}: ${p}%`)}},
   ffmpegOverride:({args})=>[...args.slice(0,-1),'-maxrate:v','5M','-bufsize:v','10M','-threads','2','-movflags','+faststart',args.at(-1)]});
 }
 fs.writeFileSync(path.join(output,`${mode}-provenance.json`),JSON.stringify({lesson_sha256:hash(pack+'/lesson.json'),pack_sha256:hash(pack+'/manifest.json'),renderer_source:process.env.DEMO_SOURCE,review_status:'pending'}));
}finally{await browser.close({silent:true})}
