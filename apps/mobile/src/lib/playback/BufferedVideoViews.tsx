import React, { useLayoutEffect, useMemo, useRef } from 'react';
import { StyleSheet, View } from 'react-native';
import { VideoView } from 'expo-video';
import type { BufferedVideoViewsProps } from './BufferedVideoViews.types';
import { DecodedFrames } from './DecodedFrames';

/** Surfaces are keyed by physical slot/source generation, never by active role.
 * Promoting a decoded standby preserves its AVPlayerViewController and frame. */
export function BufferedVideoViews({ players, playback, sourceReady, visible, fill, onFrame, adjacent }: BufferedVideoViewsProps) {
  const frames = useMemo(() => new DecodedFrames(), [players[0], players[1]]);
  const current = useRef({ playback, visible, sourceReady, onFrame });
  useLayoutEffect(() => {
    frames.observe(playback.buffers ?? []);
    current.current = { playback, visible, sourceReady, onFrame };
  }, [frames, visible, sourceReady, playback, onFrame]);
  useLayoutEffect(() => {
    if (visible && sourceReady && frames.has(playback.activeSlot)) current.current.onFrame(playback.selection);
  }, [frames, visible, sourceReady, playback.activeSlot, playback.selection]);
  return <>{players.map((player, slot) => {
    const buffer = playback.buffers?.[slot];
    const active = slot === playback.activeSlot;
    const offset = active ? (sourceReady ? 0 : null) : buffer?.ready && adjacent ? buffer.uri === adjacent.nextUrl ? adjacent.height : buffer.uri === adjacent.previousUrl ? -adjacent.height : null : null;
    return <View key={slot} pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity: visible && offset !== null ? 1 : 0, transform: [{ translateY: offset ?? 0 }] }]}>
      {buffer?.ready && <VideoView key={buffer.generation} testID={active ? 'active-video' : 'buffered-video'} style={StyleSheet.absoluteFill}
        player={player} nativeControls={false} allowsPictureInPicture={false} contentFit={fill ? 'cover' : 'contain'}
        onFirstFrameRender={() => {
          if (!frames.mark(slot, buffer.generation)) return;
          const latest = current.current;
          if (latest.visible && latest.sourceReady && latest.playback.activeSlot === slot) latest.onFrame(latest.playback.selection);
        }} />}
    </View>;
  })}</>;
}
