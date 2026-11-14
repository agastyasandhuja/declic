import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, AppState, FlatList, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useEvent } from 'expo';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { EntertainmentVideo } from '../../contracts/generated';
import { SinglePlayerController, type PlaybackState } from '../../lib/playback/SinglePlayerController';
import type { FeedSource } from './source';
import { eligibleVideos } from './source';
import { Button } from '../../components/Button';
import { theme } from '../../theme';

export interface LocalPlaybackEvent { video_id: string; event_type: 'playback_progress' | 'video_skipped' | 'playback_failed'; position_ms: number; visible_watch_ms: number }

export function FeedScreen({ source, focused, brokenClip, onEvent }: { source: FeedSource; focused: boolean; brokenClip: boolean; onEvent(event: LocalPlaybackEvent): void }) {
  const insets = useSafeAreaInsets();
  const [height, setHeight] = useState(0); const [videos, setVideos] = useState<EntertainmentVideo[]>([]);
  const [index, setIndex] = useState(0); const [viewable, setViewable] = useState(true);
  const [nextCursor, setNextCursor] = useState<string | null>(null); const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null); const [paused, setPaused] = useState(false);
  const [muted, setMuted] = useState(Platform.OS === 'web'); const [foreground, setForeground] = useState(AppState.currentState === 'active');
  const [retry, setRetry] = useState(0); const [playback, setPlayback] = useState<PlaybackState>({ loading: true, ready: false, error: null });
  const [watchMs, setWatchMs] = useState(0); const list = useRef<FlatList<EntertainmentVideo>>(null);
  const pending = useRef(false); const generation = useRef(0); const onEventRef = useRef(onEvent); onEventRef.current = onEvent;
  const watchRef = useRef(0); const videosRef = useRef(videos); videosRef.current = videos;
  const player = useVideoPlayer(null, instance => { instance.loop = true; instance.timeUpdateEventInterval = 0.5; instance.staysActiveInBackground = false; instance.audioMixingMode = 'doNotMix'; });
  const [controller] = useState(() => new SinglePlayerController({ play: () => player.play(), pause: () => player.pause(), replaceAsync: uri => player.replaceAsync({ uri }) }, setPlayback));
  const { status } = useEvent(player, 'statusChange', { status: player.status });
  const { isPlaying } = useEvent(player, 'playingChange', { isPlaying: player.playing });
  const video = videos[index];

  const fetchPage = useCallback(async (cursor: string | null = null, reset = false) => {
    if (pending.current && !reset) return;
    const request = reset ? ++generation.current : generation.current;
    pending.current = true; setLoading(true); setPageError(null);
    try {
      const page = await source.getPage(cursor);
      if (request !== generation.current) return;
      setVideos(previous => eligibleVideos(reset ? page.items : [...previous, ...page.items])); setNextCursor(page.next_cursor);
      if (reset) { setIndex(0); setViewable(true); list.current?.scrollToOffset({ offset: 0, animated: false }); }
    } catch (error) { if (request === generation.current) setPageError(error instanceof Error ? error.message : 'Unable to load the feed. Retry when connected.'); }
    finally { if (request === generation.current) { pending.current = false; setLoading(false); } }
  }, [source]);
  useEffect(() => { void fetchPage(null, true); return () => { generation.current++; }; }, [fetchPage]);
  useEffect(() => {
    const listener = AppState.addEventListener('change', state => { const active = state === 'active'; setForeground(active); controller.setGate({ foreground: active }); });
    return () => listener.remove();
  }, [controller]);
  useEffect(() => { controller.setGate({ focused: focused && viewable, foreground, manuallyPaused: paused }); }, [controller, focused, foreground, viewable, paused]);
  useEffect(() => { player.muted = muted; }, [player, muted]);
  useEffect(() => {
    if (!video) return;
    setPaused(false); watchRef.current = 0; setWatchMs(0);
    const uri = brokenClip && index === 0 ? 'https://storage.googleapis.com/gtv-videos-bucket/sample/missing-demo-clip.mp4' : video.playback.url;
    void controller.setSource(uri);
  }, [controller, video?.video_id, video?.playback.url, retry, brokenClip]);
  useEffect(() => { if (status === 'error' && playback.ready) controller.reportError(); }, [status, playback.ready, controller]);
  useEffect(() => () => controller.dispose(), [controller]);
  useEffect(() => {
    if (!focused || !foreground || !viewable || !isPlaying || !playback.ready || !video) return;
    let last = Date.now();
    const timer = setInterval(() => {
      const now = Date.now(); watchRef.current += Math.min(1000, now - last); last = now; setWatchMs(watchRef.current);
      onEventRef.current({ video_id: video.video_id, event_type: 'playback_progress', position_ms: Math.round(player.currentTime * 1000), visible_watch_ms: Math.round(watchRef.current) });
    }, 500);
    return () => clearInterval(timer);
  }, [focused, foreground, viewable, isPlaying, playback.ready, video?.video_id, player]);
  useEffect(() => { if (playback.error && video) onEventRef.current({ video_id: video.video_id, event_type: 'playback_failed', position_ms: Math.round(player.currentTime * 1000), visible_watch_ms: Math.round(watchRef.current) }); }, [playback.error, video?.video_id, player]);
  const onViewable = useRef(({ viewableItems }: { viewableItems: { isViewable: boolean; index?: number | null }[] }) => {
    const visible = viewableItems.find(item => item.isViewable && item.index !== null);
    setViewable(!!visible); if (visible?.index !== undefined && visible.index !== null) setIndex(visible.index);
  }).current;
  async function retryVideo() {
    if (!video) return;
    try {
      const fresh = await source.resolvePlayback(video.video_id);
      setVideos(previous => previous.map(item => item.video_id === video.video_id ? { ...item, playback: fresh } : item)); setRetry(value => value + 1);
    } catch { controller.reportError(); }
  }
  function skip() {
    if (video) onEventRef.current({ video_id: video.video_id, event_type: 'video_skipped', position_ms: Math.round(player.currentTime * 1000), visible_watch_ms: Math.round(watchRef.current) });
    if (index < videos.length - 1) list.current?.scrollToIndex({ index: index + 1, animated: true });
    else { void fetchPage(null, true); }
  }
  return <View testID="feed-screen" style={styles.root} onLayout={event => { if (event.nativeEvent.layout.height > 0) setHeight(event.nativeEvent.layout.height); }}>
    {videos.length > 0 && height > 0 ? <FlatList ref={list} data={videos} keyExtractor={item => item.video_id} pagingEnabled snapToInterval={height} decelerationRate="fast" showsVerticalScrollIndicator={false}
      initialNumToRender={2} maxToRenderPerBatch={2} windowSize={3} getItemLayout={(_, position) => ({ length: height, offset: height * position, index: position })}
      viewabilityConfig={{ itemVisiblePercentThreshold: 80 }} onViewableItemsChanged={onViewable} onEndReachedThreshold={0.7} onEndReached={() => { if (nextCursor) void fetchPage(nextCursor); }}
      renderItem={({ item, index: cardIndex }) => <View style={{ height, backgroundColor: '#101A11' }}>
        {cardIndex === index && <VideoView testID="active-video" style={[StyleSheet.absoluteFill, { width: '100%', height: '100%' }]} player={player} contentFit="cover" nativeControls={false} allowsPictureInPicture={false} />}
        <LinearGradient pointerEvents="none" colors={['#00000070', 'transparent', '#00000018', '#000000E8']} locations={[0, 0.35, 0.55, 1]} style={StyleSheet.absoluteFill} />
        {cardIndex === index && <Pressable accessibilityRole="button" accessibilityLabel={paused ? 'Play video' : 'Pause video'} testID="toggle-playback" onPress={() => setPaused(value => !value)} style={styles.touchArea}>
          {paused && !playback.error && <View style={styles.pauseIcon}><Ionicons name="play" size={38} color="white" /></View>}
        </Pressable>}
        {cardIndex === index && (playback.loading || (status === 'loading' && !isPlaying)) && !playback.error && <View pointerEvents="none" style={styles.center}><ActivityIndicator color={theme.colors.accent} size="large" /><Text style={styles.loadingText}>Finding your flow…</Text></View>}
        {cardIndex === index && playback.error && <View style={styles.center}><View style={styles.errorCard}><Ionicons name="cloud-offline-outline" size={30} color={theme.colors.accent} /><Text style={styles.errorTitle}>A small interruption.</Text><Text style={styles.errorText}>{playback.error}</Text><Button title="Retry clip" onPress={() => void retryVideo()} /><Button title="Skip clip" secondary onPress={skip} /></View></View>}
        <View pointerEvents="box-none" style={[styles.description, { bottom: 27 }]}><View style={styles.tag}><Ionicons name="film-outline" size={11} color={theme.colors.accent} /><Text style={styles.tagText}>{source.mode === 'fixture' ? 'SAMPLE CLIP' : item.provider.toUpperCase()}</Text></View><Text style={styles.caption}>{item.caption}</Text><Text style={styles.creator}>{item.creator.display_name ?? 'Video creator'}</Text><Text style={styles.hint}>Swipe up. Stay curious.</Text></View>
      </View>} /> : <View style={styles.center}><View style={styles.empty}><Ionicons name="play-circle-outline" size={54} color={theme.colors.accent} /><Text style={styles.errorTitle}>{loading ? 'Your feed is warming up.' : 'A fresh start.'}</Text><Text style={styles.errorText}>{pageError ?? 'No clips are available yet. Reload to try again.'}</Text>{loading ? <ActivityIndicator color={theme.colors.accent} /> : <Button title="Reload feed" onPress={() => void fetchPage(null, true)} />}</View></View>}
    <View pointerEvents="box-none" style={[styles.header, { top: insets.top + 12 }]}><Text style={styles.brand}>study / scroll</Text><View style={styles.feedLabel}><View style={styles.greenDot} /><Text style={styles.headerLabel}>{source.mode === 'fixture' ? 'DEMO FEED' : 'FOR YOU'}</Text></View><Pressable accessibilityRole="button" accessibilityLabel={muted ? 'Unmute video' : 'Mute video'} onPress={() => setMuted(value => !value)} style={styles.roundButton}><Ionicons name={muted ? 'volume-mute-outline' : 'volume-high-outline'} size={20} color="white" /></Pressable></View>
    {videos.length > 0 && <View pointerEvents="none" style={styles.counter}><Text style={styles.counterText}>{index + 1} / {videos.length}{loading ? '  ·  loading' : ''}</Text><Text style={styles.counterText}>{Math.floor(watchMs / 1000)}s watched</Text></View>}
    {pageError && videos.length > 0 && <Pressable accessibilityRole="button" onPress={() => void fetchPage(nextCursor)} style={styles.pageError}><Text style={styles.counterText}>{pageError} Tap to retry.</Text></Pressable>}
  </View>;
}
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0A100A' }, touchArea: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, alignItems: 'center', justifyContent: 'center' },
  center: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, alignItems: 'center', justifyContent: 'center', padding: 28 }, empty: { width: '100%', maxWidth: 380, gap: 18, alignItems: 'center' },
  header: { position: 'absolute', left: 23, right: 22, flexDirection: 'row', alignItems: 'center', gap: 14 }, brand: { color: '#fff', fontSize: 19, letterSpacing: -0.6, fontWeight: '700' },
  feedLabel: { flexDirection: 'row', alignItems: 'center', gap: 6, marginLeft: 'auto' }, headerLabel: { fontSize: 9, fontWeight: '800', letterSpacing: 1.4, color: '#fff' }, greenDot: { height: 5, width: 5, borderRadius: 3, backgroundColor: theme.colors.accent },
  roundButton: { width: 37, height: 37, borderRadius: 19, backgroundColor: '#FFFFFF18', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#FFFFFF25' },
  description: { position: 'absolute', left: 24, right: 65, gap: 9 }, tag: { flexDirection: 'row', alignItems: 'center', gap: 6 }, tagText: { color: theme.colors.accent, fontSize: 10, letterSpacing: 1.8, fontWeight: '700' },
  caption: { color: '#fff', fontWeight: '700', fontSize: 30, lineHeight: 34, letterSpacing: -0.8 }, creator: { color: '#E0E5DD', fontSize: 13, fontWeight: '500' }, hint: { color: '#B3BBAF', fontSize: 11, marginTop: 5 },
  counter: { position: 'absolute', right: 20, bottom: 30, gap: 5, alignItems: 'flex-end' }, counterText: { color: '#C1CCBB', fontSize: 10 }, pauseIcon: { height: 82, width: 82, borderRadius: 42, backgroundColor: '#00000050', alignItems: 'center', justifyContent: 'center' },
  loadingText: { color: '#D9E5D2', fontSize: 12, marginTop: 16 }, errorCard: { borderRadius: 26, backgroundColor: '#162016F5', borderColor: '#526148', borderWidth: 1, padding: 24, gap: 15, width: '100%', maxWidth: 350 },
  errorTitle: { color: theme.colors.text, fontSize: 24, fontWeight: '600', letterSpacing: -0.5 }, errorText: { color: theme.colors.muted, fontSize: 14, lineHeight: 21 }, pageError: { position: 'absolute', top: 110, left: 20, right: 20, padding: 14, borderRadius: 12, backgroundColor: '#283328' },
});
