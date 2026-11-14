import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';

// Invoked only inside the existing secret-free, network-disabled renderer image.
const mode=process.env.AUDITION_MODE || 'stills';
if(!['stills','video'].includes(mode)) throw new Error('Invalid render mode');
fs.cpSync('/opt/renderer/audition/src','/tmp/audition-src',{recursive:true});
fs.copyFileSync('/opt/renderer/PopCaptions.tsx','/tmp/audition-src/PopCaptions.tsx');
const serveUrl=await bundle({entryPoint:'/tmp/audition-src/Root.tsx',publicDir:'/job',outDir:'/tmp/bundle',
 webpackOverride:c=>({...c,cache:false,resolve:{...c.resolve,modules:['/opt/renderer/node_modules','node_modules']}})});
const browser=await openBrowser('chrome',{browserExecutable:'/usr/bin/chromium',chromiumOptions:{gl:'swangle'}});
try {
for(const id of fs.readdirSync('/job').sort()) {
 if(!/^[a-z-]+$/.test(id)) throw new Error('Invalid sample ID');
 if(process.env.AUDITION_ONLY && !process.env.AUDITION_ONLY.split(',').includes(id)) continue;
 const pack=path.join('/job',id);
 const lesson=JSON.parse(fs.readFileSync(path.join(pack,'lesson.json'),'utf8'));
 if(lesson.id!==id || !Number.isInteger(lesson.frames) || lesson.frames<150 || lesson.frames>1800 || lesson.segments.length!==12) throw new Error('Invalid audition');
 for(const s of lesson.segments) if(!/^speech-(?:[0-9]|1[01])\.wav$/.test(s.audio) || !Number.isFinite(s.start) || s.start<0 || s.end<=s.start) throw new Error('Invalid asset or timing');
 const output=path.join('/output',id);fs.mkdirSync(output,{recursive:true});
 const common={serveUrl,inputProps:{lesson},browserExecutable:'/usr/bin/chromium',puppeteerInstance:browser,
  chromiumOptions:{gl:'swangle'},timeoutInMilliseconds:60000,mediaCacheSizeInBytes:64*1024*1024};
 const composition=await selectComposition({...common,id:'Story'});
 if(mode==='stills') {
  const frames=[0,...lesson.segments.flatMap(s=>[Math.round((s.start+.6)*30),Math.round((s.start+s.end)/2*30)]),lesson.frames-1,2,8];
  for(const [i,f] of frames.entries()) await renderStill({...common,composition,frame:Math.min(lesson.frames-1,f),scale:.75,output:path.join(output,`frame-${i}.png`)});
  fs.writeFileSync(path.join(output,'frame-index.json'),JSON.stringify(frames));
 } else {
  const dest=path.join(output,'lesson.mp4');
  let lastProgress=-1;
  await renderMedia({...common,composition,codec:'h264',audioCodec:'aac',pixelFormat:'yuv420p',sampleRate:48000,
   onProgress:({progress})=>{const p=Math.floor(progress*10)*10;if(p!==lastProgress){lastProgress=p;console.log(`Render ${p}%`);}},
   outputLocation:dest,scale:1,concurrency:2,crf:20,
   ffmpegOverride:({args})=>[...args.slice(0,-1),'-threads','2','-movflags','+faststart',args.at(-1)]});
 }
 console.log(`${mode}: ${id} (${lesson.duration.toFixed(1)}s)`);
}
} finally {await browser.close({silent:true});}
