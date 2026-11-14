import React from 'react';
import { StyleSheet } from 'react-native';
import { VideoView } from 'expo-video';
import type { BufferedVideoViewsProps } from './BufferedVideoViews.types';

/** The adjacent buffer remains paused; the selected surface is generation-keyed. */
export function BufferedVideoViews({ players, playback, sourceReady, visible, fill, onFrame, adjacent }: BufferedVideoViewsProps) {
  if (!visible) return null;
  const standby = 1 - playback.activeSlot;
  const buffer = playback.buffers?.[standby];
  const offset = buffer?.ready && adjacent ? buffer.uri === adjacent.nextUrl ? adjacent.height : buffer.uri === adjacent.previousUrl ? -adjacent.height : null : null;
  return <>
    {offset !== null && <VideoView key={`standby:${standby}:${buffer!.uri}`} testID="buffered-video" style={[StyleSheet.absoluteFill, { transform: [{ translateY: offset }] }]}
      player={players[standby]} nativeControls={false} allowsPictureInPicture={false} contentFit={fill ? 'cover' : 'contain'} />}
    {sourceReady && <VideoView key={`active:${playback.selection}`} testID="active-video" style={StyleSheet.absoluteFill}
      player={players[playback.activeSlot]} nativeControls={false} allowsPictureInPicture={false}
      contentFit={fill ? 'cover' : 'contain'} onFirstFrameRender={() => onFrame(playback.selection)} />}
  </>;
}
