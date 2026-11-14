import React from 'react';
import {useVideoConfig} from 'remotion';

/** User-approved voxel treatment, shared by narrated formats. No invented timing. */
export const PopCaptions = ({caption, words, now, fontSize, top, left, right}: any) => {
  const {width,height}=useVideoConfig();
  const word=(words || caption?.words || []).find((w:any)=>now>=w.start&&now<w.end);
  if(!word)return null;
  const age=Math.max(0,now-word.start);
  const scale=age<.08?.9+age/.08*.14:1.04-Math.min(1,(age-.08)/.1)*.04;
  const ratio=width/720;
  return <div data-caption style={{position:'absolute',top:top??height*590/1280,
    left:left??45*ratio,right:right??75*ratio,textAlign:'center',
    fontFamily:'DejaVu Sans, sans-serif',fontWeight:900,fontSize:fontSize??58*ratio,
    color:'white',lineHeight:1.15,WebkitTextStroke:`${ratio}px #25343b`,
    paintOrder:'stroke fill',textShadow:`0 ${4*ratio}px ${3*ratio}px #0009`,
    transform:`scale(${scale})`,transformOrigin:'center center'}}>{word.text}</div>;
};
