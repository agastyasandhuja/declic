import React, { useEffect, useRef } from 'react';
import { StyleSheet, View } from 'react-native';
import { VideoView } from 'expo-video';
import type { BufferedVideoViewsProps } from './BufferedVideoViews.types';

type WebVideoView = VideoView & { nativeRef?: React.RefObject<HTMLVideoElement | null> };

/** Web players need attached video elements to retain their media and preload state. */
export function BufferedVideoViews({ players, playback, sourceReady, visible, fill, onFrame, adjacent }: BufferedVideoViewsProps) {
  const first = useRef<WebVideoView>(null); const second = useRef<WebVideoView>(null);
  const callback = useRef(onFrame); callback.current = onFrame;
  useEffect(() => {
    if (!visible || !sourceReady) return;
    const element = (playback.activeSlot === 0 ? first : second).current?.nativeRef?.current;
    if (!element) return;
    let cancelled = false; let frameId: number | undefined;
    const confirm = () => {
      if (!cancelled && element.currentSrc === playback.sourceUri && element.readyState >= 2 && element.videoWidth > 0 && element.videoHeight > 0) callback.current(playback.selection);
    };
    if (element.requestVideoFrameCallback) {
      frameId = element.requestVideoFrameCallback(confirm);
    } else {
      // loadeddata means a decoded video frame is available; audio-only data is excluded.
      element.addEventListener('loadeddata', confirm); confirm();
    }
    return () => {
      cancelled = true;
      if (frameId !== undefined) element.cancelVideoFrameCallback(frameId);
      element.removeEventListener('loadeddata', confirm);
    };
  }, [visible, sourceReady, playback.selection, playback.sourceUri, playback.activeSlot]);
  return <>{players.map((player, slot) => {
    const buffer = playback.buffers?.[slot];
    const offset = slot === playback.activeSlot ? 0 : buffer?.ready && adjacent ? buffer.uri === adjacent.nextUrl ? adjacent.height : buffer.uri === adjacent.previousUrl ? -adjacent.height : null : null;
    return <View key={slot} pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity: visible && offset !== null ? 1 : 0, transform: [{ translateY: offset ?? 0 }] }]}><VideoView ref={slot === 0 ? first : second}
      testID={slot === playback.activeSlot ? 'active-video' : 'buffered-video'}
      style={{ width: '100%', height: '100%' }}
      player={player} nativeControls={false} allowsPictureInPicture={false} contentFit={fill ? 'cover' : 'contain'} /></View>;
  })}</>;
}
