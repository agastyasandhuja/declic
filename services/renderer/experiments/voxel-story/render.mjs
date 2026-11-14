import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {bundle} from '@remotion/bundler';
import {openBrowser,renderMedia,renderStill,selectComposition} from '@remotion/renderer';

const mode=process.env.AUDITION_MODE||'stills';
if(!['stills','video'].includes(mode))throw Error('Unknown mode');
const source='/opt/renderer/audition';
const three=fs.readFileSync('/vendor/three.module.js');
if(createHash('sha256').update(three).digest('hex')!=='ce1fa418de16a19495a9f72495580e3015d7745c296d3ce0485897f902ddedfb')throw Error('Unexpected Three.js bytes');
fs.cpSync(path.join(source,'src'),'/tmp/src',{recursive:true});
fs.writeFileSync('/tmp/src/three.module.js',three);
fs.copyFileSync('/opt/renderer/PopCaptions.tsx','/tmp/src/PopCaptions.tsx');
const lesson=JSON.parse(fs.readFileSync('/job/commons-lake/lesson.json','utf8'));
const scenes=['hook','access','subtract','extra','rush','deplete','empty','commons','cost','rules','restore'];
if(lesson.id!=='commons-lake'||!Number.isInteger(lesson.frames)||lesson.frames<900||lesson.frames>1800||lesson.segments.length!==11)throw Error('Invalid lesson');
for(const [i,s]of lesson.segments.entries()){
 if(s.scene!==scenes[i]||s.audio!==`speech-${i}.wav`||!Number.isFinite(s.start)||s.start<0||s.end<=s.start||s.end>lesson.frames/30)throw Error('Invalid segment');
 for(const v of [...s.camera,s.target])if(v.length!==3||!v.every(x=>Number.isFinite(x)&&Math.abs(x)<100))throw Error('Invalid camera');
}
if(!Array.isArray(lesson.words)||lesson.words.length>300||!lesson.words.every(w=>typeof w.text==='string'&&w.text.length<50&&Number.isFinite(w.start)&&w.start>=0&&w.end>=w.start&&w.end<=lesson.frames/30))throw Error('Invalid captions');
const serveUrl=await bundle({entryPoint:'/tmp/src/Root.tsx',publicDir:'/job',outDir:'/tmp/bundle',webpackOverride:c=>({...c,cache:false,resolve:{...c.resolve,modules:['/opt/renderer/node_modules','node_modules']}})});
const browser=await openBrowser('chrome',{browserExecutable:'/usr/bin/chromium',chromiumOptions:{gl:'swangle'}});
try{
 const common={serveUrl,inputProps:{lesson},browserExecutable:'/usr/bin/chromium',puppeteerInstance:browser,chromiumOptions:{gl:'swangle'},timeoutInMilliseconds:90000,mediaCacheSizeInBytes:64*1024*1024};
 const composition=await selectComposition({...common,id:'VoxelStory'});
 const dest='/output/commons-lake';fs.mkdirSync(dest,{recursive:true});
 if(mode==='stills'){
  const frames=lesson.segments.flatMap(s=>[Math.round((s.start+.45)*30),Math.round((s.start+(s.end-s.start)*.75)*30)]);
  for(const [i,frame]of frames.entries()){await renderStill({...common,composition,frame,output:path.join(dest,`frame-${i}.png`)});console.log(`Still ${i+1}/${frames.length}`)}
  fs.writeFileSync(path.join(dest,'frame-index.json'),JSON.stringify(frames));
 }else{
  let last=-1;
  await renderMedia({...common,composition,codec:'h264',audioCodec:'aac',pixelFormat:'yuv420p',sampleRate:48000,crf:20,concurrency:2,outputLocation:path.join(dest,'lesson.mp4'),onProgress:({progress})=>{const p=Math.floor(progress*20)*5;if(p!==last){last=p;console.log(`Render ${p}%`)}},ffmpegOverride:({args})=>[...args.slice(0,-1),'-threads','2','-movflags','+faststart',args.at(-1)]});
 }
}finally{await browser.close({silent:true})}
