import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {openBrowser,renderMedia,renderStill,selectComposition} from '@remotion/renderer';
import {validatePack} from './validate.mjs';

const input=process.env.RENDER_INPUT || '/job';
const output=process.env.RENDER_OUTPUT || '/output';
const lesson=validatePack(input);
fs.mkdirSync(output,{recursive:true});
// The entire package is copied inside the sandbox. No host compiler touches scene code.
const work='/tmp/render-source';
fs.cpSync('/opt/renderer/src',work,{recursive:true});
if(lesson.custom_scene) fs.copyFileSync(path.join(input,'scene.tsx'),path.join(work,'CustomScene.tsx'));
const serveUrl=await bundle({entryPoint:path.join(work,'Root.tsx'),publicDir:path.join(input,'assets'),outDir:'/tmp/bundle',
 webpackOverride:config=>({...config,cache:false,resolve:{...config.resolve,modules:['/opt/renderer/node_modules','node_modules']}})});
const browserExecutable=process.env.CHROME_PATH || '/usr/bin/chromium';
const puppeteerInstance=await openBrowser('chrome',{browserExecutable,chromiumOptions:{gl:'swangle'}});
const common={serveUrl,inputProps:{lesson},browserExecutable,puppeteerInstance,chromiumOptions:{gl:'swangle'},timeoutInMilliseconds:60000,
 offthreadVideoThreads:1,offthreadVideoCacheSizeInBytes:64*1024*1024,mediaCacheSizeInBytes:64*1024*1024};
const composition=await selectComposition({...common,id:'Lesson'});
const shotFrames=(lesson.shots||[]).flatMap(s=>[s.start+.3,(s.start+s.end)/2,s.end-.3]).map(t=>Math.min(lesson.frame_count-1,Math.ceil(t*30)));
const beatFrames=(lesson.teaching_beats||[]).flatMap(b=>[b.start,b.speech_end,(b.speech_end+b.end)/2])
 .map(t=>Math.min(lesson.frame_count-1,Math.ceil(t*30)));
const sampleFrames=[...new Set([0,...lesson.events.map(e=>Math.min(lesson.frame_count-1,Math.ceil(e.time*30)+6)),...beatFrames,...shotFrames,...(lesson.review_frames||[]),lesson.frame_count-1])].sort((a,b)=>a-b);
fs.writeFileSync(path.join(output,'frame-index.json'),JSON.stringify(sampleFrames.map((frame,i)=>({file:`frame-${String(i).padStart(2,'0')}.png`,frame,time:frame/30}))));
for(const [i,frame] of sampleFrames.entries()) {
 await renderStill({...common,composition,frame,scale:.5,output:path.join(output,`frame-${String(i).padStart(2,'0')}.png`)});
}
if(process.env.RENDER_STILLS_ONLY!=='1') {
let lastProgress=0;
await renderMedia({...common,composition,onProgress:({renderedFrames})=>{if(renderedFrames-lastProgress>=150){lastProgress=renderedFrames;console.log(`Rendered ${renderedFrames}/${lesson.frame_count}`)}},codec:'h264',audioCodec:'aac',pixelFormat:'yuv420p',sampleRate:48000,colorSpace:'bt709',
 outputLocation:path.join(output,'lesson.mp4'),concurrency:1,crf:20,
 scale:process.env.RENDER_SCALE==='0.5'?.5:1,
 ffmpegOverride:({args})=>[...args.slice(0,-1),'-threads','2','-movflags','+faststart',args.at(-1)]});
}
await puppeteerInstance.close({silent:true});
fs.writeFileSync(path.join(output,'render-result.json'),JSON.stringify({state:'succeeded',frames:lesson.frame_count}));
