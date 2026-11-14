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
for(const [i,frame] of [...new Set([0,...lesson.events.map(e=>Math.min(lesson.frame_count-1,Math.ceil(e.time*30)+6)),lesson.frame_count-1])].entries()) {
 await renderStill({...common,composition,frame,scale:.5,output:path.join(output,`frame-${String(i).padStart(2,'0')}.png`)});
}
await renderMedia({...common,composition,codec:'h264',audioCodec:'aac',pixelFormat:'yuv420p',sampleRate:48000,colorSpace:'bt709',
 outputLocation:path.join(output,'lesson.mp4'),concurrency:1,crf:20,
 scale:process.env.RENDER_SCALE==='0.5'?.5:1,
 ffmpegOverride:({args})=>[...args.slice(0,-1),'-threads','2','-movflags','+faststart',args.at(-1)]});
await puppeteerInstance.close({silent:true});
fs.writeFileSync(path.join(output,'render-result.json'),JSON.stringify({state:'succeeded',frames:lesson.frame_count}));
