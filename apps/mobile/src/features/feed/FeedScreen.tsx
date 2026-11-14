import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, AppState, FlatList, Linking, Share, Pressable, StyleSheet, Text, View } from 'react-native';
import { useVideoPlayer, type VideoPlayer } from 'expo-video';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { EntertainmentVideo } from '../../contracts/generated';
import { BufferedVideoViews } from '../../lib/playback/BufferedVideoViews';
import { BufferedPlayerController, type BufferedPlaybackState } from '../../lib/playback/BufferedPlayerController';
import type { PlayerDriver } from '../../lib/playback/SinglePlayerController';
import { ApiError } from '../../lib/api/client';
import { VisibleWatchTracker, PlaybackStallGuard, FirstFrameGuard } from '../../lib/playback/VisibleWatchTracker';
import type { FeedSource, FeedHistory } from './source';
import { appendFeedWindow, shouldPrefetchPage, unseenVideos } from './source';
import { fetchAvailablePage } from './paging';
import { Button } from '../../components/Button';
import { Brand } from '../../components/Brand';
import type { PlaybackPreferences } from '../settings/ProfileScreen';
import { theme } from '../../theme';

export interface LocalPlaybackEvent { video_id: string; event_type: 'playback_progress' | 'video_skipped' | 'playback_failed'; position_ms: number; visible_watch_ms: number }
const setupPlayer = (instance: VideoPlayer) => {
  instance.loop = true; instance.staysActiveInBackground = false; instance.audioMixingMode = 'doNotMix';
  instance.bufferOptions = { preferredForwardBufferDuration: 5 };
};

export function FeedScreen({ source, focused, brokenClip, onEvent, onReload, preferences, setPreferences, clickedIds, savedIds, onClickVideo, onSaveVideo, history, allowReplay }: { history: FeedHistory; allowReplay: boolean; preferences: PlaybackPreferences; setPreferences(value: PlaybackPreferences): void; clickedIds: string[]; savedIds: string[]; onClickVideo(video: EntertainmentVideo): void; onSaveVideo(video: EntertainmentVideo): void; source: FeedSource; focused: boolean; brokenClip: boolean; onEvent(event: LocalPlaybackEvent): void; onReload(): void }) {
  const insets = useSafeAreaInsets();
  const [height, setHeight] = useState(0); const [videos, setVideos] = useState<EntertainmentVideo[]>([]);
  const [index, setIndex] = useState(0); const [viewable, setViewable] = useState(true);
  const [nextCursor, setNextCursor] = useState<string | null>(null); const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null); const [paused, setPaused] = useState(false);
  const [pageNeedsReset, setPageNeedsReset] = useState(false);
  const muted = preferences.muted; const setMuted = (value: boolean) => setPreferences({ ...preferences, muted: value }); const [foreground, setForeground] = useState(AppState.currentState === 'active');
  const [retry, setRetry] = useState(0);
  const [fillVideo, setFillVideo] = useState(false);
  const retryPageCount = useRef(0);
  const retryPageTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const appliedRetry = useRef(0);
  const [playback, setPlayback] = useState<BufferedPlaybackState>({ loading: true, ready: false, error: null, activeSlot: 0, timedOut: false, sourceUri: null, selection: 0 });
  const [renderedSelection, setRenderedSelection] = useState<number | null>(null);
  const firstFrame = useRef(new FirstFrameGuard()); const stalled = useRef(new PlaybackStallGuard());
  const selectionRef = useRef(playback.selection); selectionRef.current = playback.selection;
  const [watchMs, setWatchMs] = useState(0); const list = useRef<FlatList<EntertainmentVideo>>(null);
  const videosRef = useRef(videos); videosRef.current = videos;
  const pendingScrollIndex = useRef<number | null>(null);
  const pending = useRef(false); const generation = useRef(0); const requestAbort = useRef<AbortController | null>(null);
  const resumePageOnFocus = useRef(false);
  const onEventRef = useRef(onEvent); onEventRef.current = onEvent;
  const watch = useRef(new VisibleWatchTracker()); const selectedIndex = useRef(index); selectedIndex.current = index;
  const firstPlayer = useVideoPlayer(null, setupPlayer); const secondPlayer = useVideoPlayer(null, setupPlayer);
  const controller = useMemo(() => {
    const driver = (instance: VideoPlayer): PlayerDriver => ({ play: () => instance.play(), pause: () => instance.pause(), replaceAsync: uri => instance.replaceAsync({ uri }) });
    return new BufferedPlayerController([driver(firstPlayer), driver(secondPlayer)], setPlayback);
  }, [firstPlayer, secondPlayer]);
  const controllerRef = useRef(controller); controllerRef.current = controller;
  const player = playback.activeSlot === 0 ? firstPlayer : secondPlayer;
  const [observedNative, setNative] = useState({ owner: player, status: player.status, isPlaying: player.playing });
  const native = observedNative.owner === player ? observedNative : { status: player.status, isPlaying: player.playing };
  const video = videos[index];
  const selectedUri = brokenClip && index === 0 ? 'https://storage.googleapis.com/gtv-videos-bucket/sample/missing-demo-clip.mp4' : video?.playback.url;
  const sourceReady = playback.ready && playback.sourceUri === selectedUri;
  const frameRendered = renderedSelection === playback.selection;
  const focusGate = useRef(focused && foreground); focusGate.current = focused && foreground;
  const current = useRef({ video, player }); current.current = { video, player };

  const fetchPage = useCallback(async (cursor: string | null = null, reset = false) => {
    if (pending.current && !reset) return;
    if (retryPageTimer.current) { clearTimeout(retryPageTimer.current); retryPageTimer.current = null; }
    const request = reset ? ++generation.current : generation.current;
    if (reset) { requestAbort.current?.abort(); controllerRef.current.setGate({ focused: false }); videosRef.current = []; selectedIndex.current = 0; pendingScrollIndex.current = 0; setVideos([]); setIndex(0); }
    const abort = new AbortController(); requestAbort.current = abort;
    pending.current = true; setLoading(true); setPageError(null); setPageNeedsReset(false);
    try {
      const read = async (cursor: string | null) => { const page = await source.getPage(cursor, abort.signal); return { ...page, items: allowReplay ? page.items : history.unseen(page.items) }; };
      const page = await fetchAvailablePage({ ...source, getPage: read }, reset ? [] : videosRef.current, cursor, abort.signal, next => {
        if (request === generation.current && !abort.signal.aborted) { cursor = next; setNextCursor(next); }
      });
      if (request !== generation.current || abort.signal.aborted) return;
      if (!unseenVideos(reset ? [] : videosRef.current, page.items).length && page.next_cursor) {
        setNextCursor(page.next_cursor);
        throw new Error('No new clips were available in this window. Keep watching and retry shortly.');
      }
      const window = appendFeedWindow(reset ? [] : videosRef.current, page.items, reset ? 0 : selectedIndex.current);
      if (window.removed) { controllerRef.current.setGate({ focused: false }); pendingScrollIndex.current = window.index; }
      videosRef.current = window.items; selectedIndex.current = window.index;
      setVideos(window.items); setIndex(window.index);
      setNextCursor(page.next_cursor); retryPageCount.current = 0;
      if (reset) setViewable(true);
    } catch (error) { if (request === generation.current && !abort.signal.aborted) { setPageNeedsReset(error instanceof ApiError && error.code === 'STALE_CURSOR'); if (error instanceof ApiError && error.retryable && error.code !== 'INSTAGRAM_BUSY' && retryPageCount.current < 2) { retryPageCount.current++; retryPageTimer.current = setTimeout(() => { if (request === generation.current && focusGate.current) void fetchPage(cursor, reset); }, 3000 * retryPageCount.current); } setPageError(error instanceof Error ? error.message : 'Unable to load the feed. Retry when connected.'); } }
    finally { if (request === generation.current) { pending.current = false; setLoading(false); } }
  }, [source, history, allowReplay]);
  useEffect(() => { void fetchPage(null, true); return () => { generation.current++; requestAbort.current?.abort(); if (retryPageTimer.current) clearTimeout(retryPageTimer.current); }; }, [fetchPage]);
  useEffect(() => {
    if (!focused || !foreground) {
      if (pending.current) { resumePageOnFocus.current = true; requestAbort.current?.abort(); }
    } else if (resumePageOnFocus.current && !loading) {
      resumePageOnFocus.current = false;
      void fetchPage(nextCursor, !videosRef.current.length && !nextCursor);
    }
  }, [focused, foreground, loading, nextCursor, fetchPage]);
  useLayoutEffect(() => {
    if (pendingScrollIndex.current !== null && height > 0 && videos.length) {
      list.current?.scrollToOffset({ offset: pendingScrollIndex.current * height, animated: false });
      pendingScrollIndex.current = null;
      controller.setGate({ focused: focused && foreground && viewable });
    }
  }, [videos, height, controller, focused, foreground, viewable]);
  useEffect(() => {
    if (shouldPrefetchPage({ index, count: videos.length, hasNext: !!nextCursor, focused, foreground, loading, hasError: !!pageError })) void fetchPage(nextCursor);
  }, [index, videos.length, nextCursor, focused, foreground, loading, pageError, fetchPage]);
  useEffect(() => {
    const listener = AppState.addEventListener('change', state => {
      const active = state === 'active'; controller.setGate({ foreground: active }); setForeground(active);
      watch.current.sample(player.currentTime * 1000, Date.now(), false);
    });
    return () => listener.remove();
  }, [controller, player]);
  // Layout cleanup silences both drivers before Expo releases their native objects.
  useLayoutEffect(() => () => controller.dispose(), [controller]);
  useLayoutEffect(() => { controller.setGate({ focused: focused && viewable, foreground, manuallyPaused: paused }); }, [controller, focused, foreground, viewable, paused]);
  useEffect(() => { firstPlayer.muted = muted; secondPlayer.muted = muted; }, [firstPlayer, secondPlayer, muted]);
  useEffect(() => {
    setNative({ owner: player, status: player.status, isPlaying: player.playing });
    const status = player.addListener('statusChange', event => setNative(value => value.owner === player ? { ...value, status: event.status } : value));
    const playing = player.addListener('playingChange', event => setNative(value => value.owner === player ? { ...value, isPlaying: event.isPlaying } : value));
    return () => { status.remove(); playing.remove(); };
  }, [player]);
  useEffect(() => { watch.current = new VisibleWatchTracker(); stalled.current = new PlaybackStallGuard(); setWatchMs(0); setPaused(false); if (video && !allowReplay) history.remember(video); }, [video?.video_id, history, allowReplay]);
  useEffect(() => {
    controller.setGate({ focused: !!video && focusGate.current && viewable });
    if (!video) return;
    let cancelled = false;
    const force = retry !== appliedRetry.current; appliedRetry.current = retry;
    const select = async () => {
      try {
        let playback = video.playback;
        if (playback.expires_at && Date.parse(playback.expires_at) <= Date.now()) {
          controller.setGate({ focused: false });
          playback = await source.resolvePlayback(video.video_id);
          if (cancelled) return;
          if (playback.expires_at && Date.parse(playback.expires_at) <= Date.now()) throw new Error('Expired playback');
          setVideos(previous => previous.map(item => item.video_id === video.video_id ? { ...item, playback } : item));
          controller.setGate({ focused: focusGate.current && viewable });
        }
        const uri = brokenClip && index === 0 ? 'https://storage.googleapis.com/gtv-videos-bucket/sample/missing-demo-clip.mp4' : playback.url;
        if (!cancelled) void controller.setSelection(uri, videos[index + 1]?.playback.url, force);
      } catch { if (!cancelled) controller.reportError(); }
    };
    void select();
    return () => { cancelled = true; };
  }, [controller, source, video?.video_id, video?.playback.url, video?.playback.expires_at, retry, brokenClip]);
  // React has now attached the selected surface; reapply the existing playback gates.
  useEffect(() => { if (sourceReady) controller.setGate({}); }, [controller, sourceReady, playback.selection]);
  useEffect(() => { if (playback.ready) controller.preload(videos[index + 1]?.playback.url); }, [controller, playback.ready, videos[index + 1]?.playback.url]);
  useEffect(() => { if (native.status === 'error' && sourceReady) controller.reportError(); }, [native.status, sourceReady, controller]);
  useEffect(() => {
    const enabled = !!video && sourceReady && focused && foreground && viewable && !paused;
    firstFrame.current.sample(playback.selection, frameRendered, Date.now(), enabled);
    const timer = setInterval(() => {
      if (firstFrame.current.sample(playback.selection, frameRendered, Date.now(), enabled)) controller.reportError(true);
    }, 250);
    return () => clearInterval(timer);
  }, [controller, video?.video_id, playback.selection, sourceReady, frameRendered, focused, foreground, viewable, paused]);
  useEffect(() => {
    const eligible = focused && foreground && viewable && native.isPlaying && native.status === 'readyToPlay' && sourceReady && frameRendered && !paused;
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    if (!video) return;
    const enabled = focused && foreground && viewable && sourceReady && !paused;
    stalled.current.sample(player.currentTime * 1000, Date.now(), enabled);
    const timer = setInterval(() => {
      const position = Math.max(0, Math.round(player.currentTime * 1000));
      if (stalled.current.sample(position, Date.now(), enabled)) controller.reportError(true);
      const total = watch.current.sample(position, Date.now(), eligible, player.duration * 1000);
      setWatchMs(total);
      if (eligible) onEventRef.current({ video_id: video.video_id, event_type: 'playback_progress', position_ms: position, visible_watch_ms: Math.round(total) });
    }, 500);
    return () => clearInterval(timer);
  }, [focused, foreground, viewable, native.isPlaying, native.status, playback.ready, sourceReady, frameRendered, paused, video?.video_id, player]);
  useEffect(() => { if (playback.error && video) onEventRef.current({ video_id: video.video_id, event_type: 'playback_failed', position_ms: Math.round(player.currentTime * 1000), visible_watch_ms: Math.round(watch.current.totalMs) }); }, [playback.error, video?.video_id, player]);
  const recordSkip = useRef(() => {});
  recordSkip.current = () => {
    const value = current.current;
    if (value.video) onEventRef.current({ video_id: value.video.video_id, event_type: 'video_skipped', position_ms: Math.round(value.player.currentTime * 1000), visible_watch_ms: Math.round(watch.current.totalMs) });
  };
  const onViewable = useRef(({ viewableItems }: { viewableItems: { isViewable: boolean; index?: number | null; item: EntertainmentVideo }[] }) => {
    const visible = viewableItems.find(item => item.isViewable && item.index != null);
    // Native callbacks can refer to the previous window while old cards are evicted.
    const located = visible ? videosRef.current.findIndex(item => item.video_id === visible.item.video_id) : -1;
    if (visible && located < 0) return; // Ignore a late callback for an evicted card.
    const next = located < 0 ? undefined : located;
    // Gate audio synchronously while no card crosses the visibility threshold.
    controllerRef.current.setGate({ focused: next != null && focusGate.current });
    setViewable(next != null);
    if (next != null && next !== selectedIndex.current) { recordSkip.current(); selectedIndex.current = next; setIndex(next); }
  }).current;
  async function retryVideo() {
    if (!video) return;
    const selected = video.video_id; const request = generation.current;
    try {
      const fresh = await source.resolvePlayback(selected);
      if (request !== generation.current || current.current.video?.video_id !== selected) return;
      setVideos(previous => previous.map(item => item.video_id === selected ? { ...item, playback: fresh } : item)); setRetry(value => value + 1);
    } catch { if (current.current.video?.video_id === selected) controller.reportError(); }
  }
  function skip() {
    if (index < videos.length - 1) list.current?.scrollToIndex({ index: index + 1, animated: !preferences.reducedMotion });
    else if (nextCursor) { if (!pageNeedsReset) void fetchPage(nextCursor); else onReload(); }
    // A finished batch must not silently loop back to the first clip.
    else setPageError('You’re caught up. Fresh clips will appear when you reload.');
  }
  return <View testID="feed-screen" style={styles.root} onLayout={event => { if (event.nativeEvent.layout.height > 0) setHeight(event.nativeEvent.layout.height); }}>
    <BufferedVideoViews players={[firstPlayer, secondPlayer]} playback={playback} sourceReady={sourceReady} visible={videos.length > 0 && height > 0} fill={fillVideo} onFrame={selection => { if (selectionRef.current === selection) setRenderedSelection(selection); }} />
    {videos.length > 0 && height > 0 ? <FlatList ref={list} data={videos} extraData={index} removeClippedSubviews={false} keyExtractor={item => item.video_id} pagingEnabled snapToInterval={height} decelerationRate="fast" showsVerticalScrollIndicator={false}
      initialNumToRender={2} maxToRenderPerBatch={2} windowSize={3} getItemLayout={(_, position) => ({ length: height, offset: height * position, index: position })}
      viewabilityConfig={{ itemVisiblePercentThreshold: 80 }} onViewableItemsChanged={onViewable}
      renderItem={({ item, index: cardIndex }) => <View style={{ height, backgroundColor: 'transparent' }}>
        <LinearGradient pointerEvents="none" colors={['#00000070', 'transparent', '#00000018', '#000000E8']} locations={[0, 0.35, 0.55, 1]} style={StyleSheet.absoluteFill} />
        {cardIndex === index && <Pressable accessibilityRole="button" accessibilityLabel={paused ? 'Play video' : 'Pause video'} testID="toggle-playback" onPress={() => setPaused(value => !value)} style={styles.touchArea}>
          {paused && !playback.error && <View style={styles.pauseIcon}><Ionicons name="play" size={38} color="white" /></View>}
        </Pressable>}
        {cardIndex === index && (!sourceReady || !frameRendered || (native.status === 'loading' && !native.isPlaying)) && !playback.error && <View pointerEvents="none" style={styles.center}><ActivityIndicator color={theme.colors.accent} size="large" /><Text style={styles.loadingText}>Finding your flow…</Text></View>}
        {cardIndex === index && playback.error && <View style={styles.center}><View style={styles.errorCard}><Ionicons name="cloud-offline-outline" size={30} color={theme.colors.accent} /><Text style={styles.errorTitle}>A small interruption.</Text><Text style={styles.errorText}>{playback.error}</Text><Button title="Retry clip" onPress={() => void retryVideo()} /><Button title="Skip clip" secondary onPress={skip} />{playback.timedOut && <Button title="Reload feed" secondary onPress={onReload} />}</View></View>}
        <View pointerEvents="box-none" style={[styles.description, { bottom: 27 }]}><View style={styles.tag}><Ionicons name="film-outline" size={11} color={theme.colors.accent} /><Text style={styles.tagText}>{source.mode === 'fixture' ? 'SAMPLE CLIP' : item.provider.toUpperCase()}</Text></View><Text style={styles.creator}>{item.creator.display_name ?? item.creator.handle ?? 'Video creator'}</Text>{preferences.captions && <Text style={styles.caption} maxFontSizeMultiplier={1.4} numberOfLines={3}>{item.caption}</Text>}
          {(item.source_url || item.creator.attribution_url) && <Pressable accessibilityRole="link" accessibilityLabel="Open original video source" onPress={() => { void Linking.openURL(item.source_url ?? item.creator.attribution_url!).catch(() => setPageError('Unable to open the source link.')); }}><Text style={styles.hint}>View original ↗</Text></Pressable>}
          <Text style={styles.hint}>Swipe up. Stay curious.</Text>
          {cardIndex === videos.length - 1 && !nextCursor && <Pressable accessibilityRole="button" onPress={onReload}><Text style={styles.hint}>End of this batch · Reload feed</Text></Pressable>}
        </View>
      </View>} /> : <View style={styles.center}><View style={styles.empty}><Ionicons name="play-circle-outline" size={54} color={theme.colors.accent} /><Text style={styles.errorTitle}>{loading ? 'Your feed is warming up.' : 'You’re all caught up.'}</Text><Text style={styles.errorText}>{pageError ?? 'No new clips are available right now. Check again in a little while.'}</Text>{loading ? <ActivityIndicator color={theme.colors.accent} /> : <Button title={nextCursor ? 'Try next page' : 'Reload feed'} onPress={() => void fetchPage(nextCursor, !nextCursor)} />}</View></View>}
    <View pointerEvents="box-none" style={[styles.header, { top: insets.top + 12 }]}><Brand size={25} /><View style={styles.feedLabel}><View style={styles.greenDot} /><Text style={styles.headerLabel}>{source.mode === 'fixture' ? 'DEMO' : source.mode === 'saved_instagram' ? 'SAVED REELS' : 'FOR YOU'}</Text></View><Pressable accessibilityRole="button" accessibilityLabel={fillVideo ? 'Fit whole video' : 'Fill screen'} onPress={() => setFillVideo(value => !value)} style={styles.roundButton}><Ionicons name={fillVideo ? 'contract-outline' : 'expand-outline'} size={18} color="white" /></Pressable><Pressable accessibilityRole="button" accessibilityLabel={muted ? 'Unmute video' : 'Mute video'} onPress={() => setMuted(!muted)} style={styles.roundButton}><Ionicons name={muted ? 'volume-mute-outline' : 'volume-high-outline'} size={20} color="white" /></Pressable></View>
    {__DEV__ && videos.length > 0 && <View pointerEvents="none" style={styles.counter}><Text style={styles.counterText}>{index + 1} / {videos.length}{loading ? '  ·  loading' : ''}</Text><Text style={styles.counterText}>{Math.floor(watchMs / 1000)}s watched</Text></View>}
    {videos.length > 0 && (index < videos.length - 1 || nextCursor) && <Pressable accessibilityRole="button" accessibilityLabel={index < videos.length - 1 ? 'Next clip' : nextCursor ? 'Load more clips' : 'Reload feed'} testID="next-clip" onPress={skip} style={[styles.roundButton, { position: 'absolute', right: 20, bottom: 58 }]}><Ionicons name={index < videos.length - 1 || nextCursor ? 'chevron-up' : 'refresh'} size={20} color="white" /></Pressable>}
    {video && <View style={styles.actions}>
      <Pressable accessibilityRole="button" accessibilityLabel={clickedIds.includes(video.video_id) ? 'Unclick video' : 'This clicks'} accessibilityState={{ selected: clickedIds.includes(video.video_id) }} onPress={() => onClickVideo(video)} style={styles.action}><Ionicons name={clickedIds.includes(video.video_id) ? 'heart' : 'heart-outline'} size={30} color={clickedIds.includes(video.video_id) ? theme.colors.coral : theme.colors.text} /><Text style={styles.actionLabel}>Clicks</Text></Pressable>
      <Pressable accessibilityRole="button" accessibilityLabel={savedIds.includes(video.video_id) ? 'Unsave video' : 'Save video'} accessibilityState={{ selected: savedIds.includes(video.video_id) }} onPress={() => onSaveVideo(video)} style={styles.action}><Ionicons name={savedIds.includes(video.video_id) ? 'bookmark' : 'bookmark-outline'} size={28} color={savedIds.includes(video.video_id) ? theme.colors.accent : theme.colors.text} /><Text style={styles.actionLabel}>Save</Text></Pressable>
      {video.source_url && <Pressable accessibilityRole="button" accessibilityLabel="Share original video" onPress={() => { void Share.share({ message: video.source_url! }).catch(() => setPageError('Unable to open sharing. Please retry.')); }} style={styles.action}><Ionicons name="arrow-redo-outline" size={28} color={theme.colors.text} /><Text style={styles.actionLabel}>Share</Text></Pressable>}
    </View>}
    {video && <View pointerEvents="none" style={styles.progress}><View style={{ height: 3, backgroundColor: theme.colors.accent, width: `${Math.min(100, Math.max(0, player.duration ? player.currentTime / player.duration * 100 : 0))}%` }} /></View>}
    {pageError && videos.length > 0 && <Pressable accessibilityRole="button" onPress={() => pageNeedsReset ? onReload() : void fetchPage(nextCursor)} style={styles.pageError}><Text style={styles.counterText}>{pageError} {pageNeedsReset ? 'Tap to reload.' : 'Tap to retry.'}</Text></Pressable>}
  </View>;
}
const styles = StyleSheet.create({
  actions: { position: 'absolute', right: 13, bottom: 125, gap: 18 }, action: { alignItems: 'center', justifyContent: 'center', minWidth: 48, minHeight: 48, gap: 4 }, actionLabel: { color: theme.colors.text, fontSize: 11, fontWeight: '600' }, progress: { position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, backgroundColor: '#FFFFFF30' }, root: { flex: 1, backgroundColor: theme.colors.background }, touchArea: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, alignItems: 'center', justifyContent: 'center' },
  center: { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, alignItems: 'center', justifyContent: 'center', padding: 28 }, empty: { width: '100%', maxWidth: 380, gap: 18, alignItems: 'center' },
  header: { position: 'absolute', left: 23, right: 22, flexDirection: 'row', alignItems: 'center', gap: 8 }, brand: { color: '#fff', fontSize: 19, letterSpacing: -0.6, fontWeight: '700' },
  feedLabel: { flexDirection: 'row', alignItems: 'center', gap: 6, marginLeft: 'auto' }, headerLabel: { fontSize: 11, fontWeight: '800', letterSpacing: 1.4, color: '#fff' }, greenDot: { height: 5, width: 5, borderRadius: 3, backgroundColor: theme.colors.accent },
  roundButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#FFFFFF18', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#FFFFFF25' },
  description: { position: 'absolute', left: 24, right: 78, gap: 9 }, tag: { flexDirection: 'row', alignItems: 'center', gap: 6 }, tagText: { color: theme.colors.accent, fontSize: 10, letterSpacing: 1.8, fontWeight: '700' },
  caption: { color: '#fff', fontWeight: '700', fontSize: 18, lineHeight: 25, letterSpacing: -0.8 }, creator: { color: '#E0E5DD', fontSize: 13, fontWeight: '500' }, hint: { color: '#B3BBAF', fontSize: 11, marginTop: 5 },
  counter: { position: 'absolute', right: 20, bottom: 30, gap: 5, alignItems: 'flex-end' }, counterText: { color: theme.colors.muted, fontSize: 10 }, pauseIcon: { height: 82, width: 82, borderRadius: 42, backgroundColor: '#00000050', alignItems: 'center', justifyContent: 'center' },
  loadingText: { color: '#D9E5D2', fontSize: 12, marginTop: 16 }, errorCard: { borderRadius: 26, backgroundColor: '#16161BF5', borderColor: theme.colors.border, borderWidth: 1, padding: 24, gap: 15, width: '100%', maxWidth: 350 },
  errorTitle: { color: theme.colors.text, fontSize: 24, fontWeight: '600', letterSpacing: -0.5 }, errorText: { color: theme.colors.muted, fontSize: 14, lineHeight: 21 }, pageError: { position: 'absolute', top: 110, left: 20, right: 20, padding: 14, borderRadius: 12, backgroundColor: theme.colors.surface },
});
