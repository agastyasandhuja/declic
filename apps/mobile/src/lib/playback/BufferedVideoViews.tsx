import React from 'react';
import { StyleSheet } from 'react-native';
import { VideoView } from 'expo-video';
import type { BufferedVideoViewsProps } from './BufferedVideoViews.types';

/** Reattach the native surface for every selected source, outside recycled list cells. */
export function BufferedVideoViews({ players, playback, sourceReady, visible, fill, onFrame }: BufferedVideoViewsProps) {
  if (!visible || !sourceReady) return null;
  return <VideoView key={playback.selection} testID="active-video" style={StyleSheet.absoluteFill}
    player={players[playback.activeSlot]} nativeControls={false} allowsPictureInPicture={false}
    contentFit={fill ? 'cover' : 'contain'} onFirstFrameRender={() => onFrame(playback.selection)} />;
}
