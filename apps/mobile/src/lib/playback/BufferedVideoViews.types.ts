import type { VideoPlayer } from 'expo-video';
import type { BufferedPlaybackState } from './BufferedPlayerController';

export interface BufferedVideoViewsProps {
  players: [VideoPlayer, VideoPlayer];
  playback: BufferedPlaybackState;
  sourceReady: boolean;
  visible: boolean;
  fill: boolean;
  onFrame(selection: number): void;
}
