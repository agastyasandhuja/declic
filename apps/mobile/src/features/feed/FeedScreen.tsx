import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, AppState, FlatList, Linking, Share, Pressable, StyleSheet, Text, View } from 'react-native';
import { useVideoPlayer, type VideoPlayer } from 'expo-video';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { EntertainmentVideo } from '../../contracts/generated';
import { PlaybackRecovery, PlaybackSeek, needsPlaybackRefresh } from '../../lib/playback/PlaybackRecovery';
import { BufferedVideoViews } from '../../lib/playback/BufferedVideoViews';
import { BufferedPlayerController, type BufferedPlaybackState } from '../../lib/playback/BufferedPlayerController';
import type { PlayerDriver } from '../../lib/playback/SinglePlayerController';
import { ApiError } from '../../lib/api/client';
import { VisibleWatchTracker, PlaybackStallGuard, FirstFrameGuard } from '../../lib/playback/VisibleWatchTracker';
import type { FeedSource, FeedHistory } from './source';
import { appendFeedWindow, shouldPrefetchPage, unseenVideos } from './source';
import { fetchRefillPage } from './paging';
import { Button } from '../../components/Button';
import { FeedCaption, FeedHeader, FeedIconButton, FeedScrim, feedRail } from './FeedChrome';
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
  const [fillVideo, setFillVideo] = useState(false);
  const resumeSeek = useRef(new PlaybackSeek());
  const recovery = useRef(new PlaybackRecovery()); const retryingVideo = useRef<string | null>(null);
  const viewableRef = useRef(viewable); viewableRef.current = viewable;
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
    const driver = (instance: VideoPlayer): PlayerDriver => ({ play: () => instance.play(), pause: () => instance.pause(), seekTo: seconds => { instance.currentTime = seconds; }, replaceAsync: uri => instance.replaceAsync({ uri }) });
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
    const request = reset ? ++generation.current : generation.current;
    if (reset) { requestAbort.current?.abort(); controllerRef.current.setGate({ focused: false }); videosRef.current = []; selectedIndex.current = 0; pendingScrollIndex.current = 0; setVideos([]); setIndex(0); }
    const abort = new AbortController(); requestAbort.current = abort;
    pending.current = true; setLoading(true); setPageError(null); setPageNeedsReset(false);
    try {
      const read = async (cursor: string | null) => { const page = await source.getPage(cursor, abort.signal); return { ...page, items: allowReplay ? page.items : history.unseen(page.items) }; };
      const page = await fetchRefillPage({ ...source, getPage: read }, reset ? [] : videosRef.current, cursor, abort.signal, next => {
        if (request === generation.current && !abort.signal.aborted) { cursor = next; setNextCursor(next); }
      });
      if (request !== generation.current || abort.signal.aborted) return;
      if (!unseenVideos(reset ? [] : videosRef.current, page.items).length && page.next_cursor) {
        setNextCursor(page.next_cursor);
        throw new Error('Instagram is repeating clips. Tap to continue looking for new Reels.');
      }
      const window = appendFeedWindow(reset ? [] : videosRef.current, page.items, reset ? 0 : selectedIndex.current);
      if (window.removed) { controllerRef.current.setGate({ focused: false }); pendingScrollIndex.current = window.index; }
      videosRef.current = window.items; selectedIndex.current = window.index;
      setVideos(window.items); setIndex(window.index);
      setNextCursor(page.next_cursor);
      if (reset) setViewable(true);
    } catch (error) { if (request === generation.current && !abort.signal.aborted) { setPageNeedsReset(error instanceof ApiError && error.code === 'STALE_CURSOR'); setPageError(error instanceof Error ? error.message : 'Unable to load the feed. Retry when connected.'); } }
    finally { if (request === generation.current) { pending.current = false; setLoading(false); } }
  }, [source, history, allowReplay]);
  useEffect(() => { void fetchPage(null, true); return () => { generation.current++; requestAbort.current?.abort(); }; }, [fetchPage]);
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
      controller.setGate({ focused: focused && foreground && viewable && !!video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== video.video_id });
    }
  }, [videos, height, controller, focused, foreground, viewable]);
  useEffect(() => {
    if (shouldPrefetchPage({ index, count: videos.length, hasNext: !!nextCursor, focused, foreground, loading, hasError: !!pageError })) void fetchPage(nextCursor);
  }, [index, videos.length, nextCursor, focused, foreground, loading, pageError, fetchPage]);
  useEffect(() => {
    const listener = AppState.addEventListener('change', state => {
      const active = state === 'active'; const stale = needsPlaybackRefresh(current.current.video?.playback.expires_at); controller.setGate({ foreground: active, ...(active && stale ? { focused: false } : {}) }); if (!active) focusGate.current = false; setForeground(active);
      watch.current.sample(player.currentTime * 1000, Date.now(), false);
    });
    return () => listener.remove();
  }, [controller, player]);
  // Layout cleanup silences both drivers before Expo releases their native objects.
  useLayoutEffect(() => () => controller.dispose(), [controller]);
  useLayoutEffect(() => {
    recovery.current.observe(video?.video_id ?? null, focused && foreground && viewable);
    controller.setGate({ focused: focused && viewable && !!video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== video.video_id, foreground, manuallyPaused: paused });
  }, [controller, focused, foreground, viewable, paused, video?.video_id, video?.playback.expires_at]);
  useEffect(() => { firstPlayer.muted = muted; secondPlayer.muted = muted; }, [firstPlayer, secondPlayer, muted]);
  useEffect(() => {
    setNative({ owner: player, status: player.status, isPlaying: player.playing });
    const status = player.addListener('statusChange', event => setNative(value => value.owner === player ? { ...value, status: event.status } : value));
    const playing = player.addListener('playingChange', event => setNative(value => value.owner === player ? { ...value, isPlaying: event.isPlaying } : value));
    return () => { status.remove(); playing.remove(); };
  }, [player]);
  useEffect(() => { resumeSeek.current.clear(); watch.current = new VisibleWatchTracker(); stalled.current = new PlaybackStallGuard(); setWatchMs(0); setPaused(false); if (video && !allowReplay) history.remember(video); }, [video?.video_id, history, allowReplay]);
  useEffect(() => {
    if (!video || needsPlaybackRefresh(video.playback.expires_at) || retryingVideo.current === video.video_id) return;
    controller.setGate({ focused: focusGate.current && viewableRef.current });
    const uri = brokenClip && index === 0 ? 'https://storage.googleapis.com/gtv-videos-bucket/sample/missing-demo-clip.mp4' : video.playback.url;
    void controller.setSelection(uri, videos[index + 1]?.playback.url);
  }, [controller, video?.video_id, video?.playback.url, video?.playback.expires_at, brokenClip]);
  useEffect(() => {
    if (video && focused && foreground && viewable && (needsPlaybackRefresh(video.playback.expires_at) || (playback.error && playback.sourceUri === video.playback.url)) && recovery.current.claim(video.video_id)) void retryVideo();
  }, [video?.video_id, focused, foreground, viewable, video?.playback.expires_at, video?.playback.url, playback.error, playback.sourceUri]);
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
      if (resumeSeek.current.isPending(video.video_id)) {
        const settled = resumeSeek.current.settled(video.video_id, position, player.duration * 1000, Date.now());
        watch.current.sample(position, Date.now(), false);
        if (settled === 'timeout' && sourceReady) controller.reportError(true);
        return;
      }
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
    controllerRef.current.setGate({ focused: next != null && focusGate.current && !needsPlaybackRefresh(visible?.item.playback.expires_at) && retryingVideo.current !== visible?.item.video_id });
    setViewable(next != null);
    if (next != null && next !== selectedIndex.current) { recordSkip.current(); selectedIndex.current = next; setIndex(next); }
  }).current;
  async function retryVideo() {
    if (!video || retryingVideo.current === video.video_id) return;
    const selected = video.video_id; const request = generation.current;
    retryingVideo.current = selected;
    resumeSeek.current.capture(selected, player.currentTime * 1000, playback.selection);
    controller.setGate({ focused: false }); setRenderedSelection(null);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    try {
      const fresh = await source.resolvePlayback(selected);
      if (request !== generation.current || current.current.video?.video_id !== selected) return;
      if (needsPlaybackRefresh(fresh.expires_at)) throw new Error('Expired playback');
      setVideos(previous => previous.map(item => item.video_id === selected ? { ...item, playback: fresh } : item));
      await controller.setSelection(fresh.url, videosRef.current[selectedIndex.current + 1]?.playback.url, true);
      if (request === generation.current && current.current.video?.video_id === selected) controller.setGate({ focused: focusGate.current && viewableRef.current });
    } catch { if (request === generation.current && current.current.video?.video_id === selected) controller.reportError(); }
    finally { if (retryingVideo.current === selected) retryingVideo.current = null; }
  }
  function skip() {
    if (index < videos.length - 1) list.current?.scrollToIndex({ index: index + 1, animated: !preferences.reducedMotion });
    else if (nextCursor) { if (!pageNeedsReset) void fetchPage(nextCursor); else onReload(); }
    // A finished batch must not silently loop back to the first clip.
    else setPageError('You’re caught up. Fresh clips will appear when you reload.');
  }
  const liked = !!video && clickedIds.includes(video.video_id);
  const saved = !!video && savedIds.includes(video.video_id);
  function onFrame(selection: number) {
    if (selectionRef.current !== selection) return;
    const id = current.current.video?.video_id;
    const target = id ? resumeSeek.current.takeTarget(id, selection, Date.now()) : null;
    if (target !== null) { controller.seekTo(target / 1000); watch.current.sample(target, Date.now(), false); }
    setRenderedSelection(selection);
  }
  return <View testID="feed-screen" style={styles.root} onLayout={event => { if (event.nativeEvent.layout.height > 0) setHeight(event.nativeEvent.layout.height); }}>
    <BufferedVideoViews players={[firstPlayer, secondPlayer]} playback={playback} sourceReady={sourceReady} visible={videos.length > 0 && height > 0} fill={fillVideo} onFrame={onFrame} />
    {videos.length > 0 && height > 0 ? <FlatList ref={list} data={videos} extraData={index} removeClippedSubviews={false} keyExtractor={item => item.video_id} pagingEnabled snapToInterval={height} decelerationRate="fast" showsVerticalScrollIndicator={false}
      initialNumToRender={2} maxToRenderPerBatch={2} windowSize={3} getItemLayout={(_, position) => ({ length: height, offset: height * position, index: position })}
      viewabilityConfig={{ itemVisiblePercentThreshold: 80 }} onViewableItemsChanged={onViewable}
      renderItem={({ item, index: cardIndex }) => <View style={{ height, backgroundColor: 'transparent' }}>
        <FeedScrim />
        {cardIndex === index && <Pressable accessibilityRole="button" accessibilityLabel={paused ? 'Play video' : 'Pause video'} testID="toggle-playback" onPress={() => setPaused(value => !value)} style={styles.touchArea}>
          {paused && !playback.error && <View style={styles.pauseIcon}><Ionicons name="play" size={38} color="white" /></View>}
        </Pressable>}
        {cardIndex === index && (!sourceReady || !frameRendered || (native.status === 'loading' && !native.isPlaying)) && !playback.error && <View pointerEvents="none" style={styles.center}><ActivityIndicator color={theme.colors.accent} size="large" /><Text style={styles.loadingText}>Finding your flow…</Text></View>}
        {cardIndex === index && playback.error && <View style={styles.center}><View style={styles.errorCard}><Ionicons name="cloud-offline-outline" size={30} color={theme.colors.accent} /><Text style={styles.errorTitle}>A small interruption.</Text><Text style={styles.errorText}>{playback.error}</Text><Button title="Retry clip" onPress={() => void retryVideo()} /><Button title="Skip clip" secondary onPress={skip} />{playback.timedOut && <Button title="Reload feed" secondary onPress={onReload} />}</View></View>}
        <FeedCaption byline={item.creator.display_name ?? item.creator.handle} caption={preferences.captions ? item.caption : undefined}>
          {(item.source_url || item.creator.attribution_url) && <Pressable accessibilityRole="link" accessibilityLabel="Open original video source" onPress={() => { void Linking.openURL(item.source_url ?? item.creator.attribution_url!).catch(() => setPageError('Unable to open the source link.')); }}><Text style={styles.hint}>View original ↗</Text></Pressable>}
        </FeedCaption>
      </View>} /> : <View style={styles.center}><View style={styles.empty}><Ionicons name="play-circle-outline" size={54} color={theme.colors.accent} /><Text style={styles.errorTitle}>{loading ? 'Your feed is warming up.' : 'You’re all caught up.'}</Text><Text style={styles.errorText}>{pageError ?? 'No new clips are available right now. Check again in a little while.'}</Text>{loading ? <ActivityIndicator color={theme.colors.accent} /> : <Button title={nextCursor ? 'Try next page' : 'Reload feed'} onPress={() => void fetchPage(nextCursor, !nextCursor)} />}</View></View>}
    <FeedHeader top={insets.top + 8} muted={muted} fill={fillVideo} onMute={video ? () => setMuted(!muted) : undefined} onFill={video ? () => setFillVideo(value => !value) : undefined} />
    {video && <View pointerEvents="box-none" style={feedRail}>
      <FeedIconButton label={liked ? 'Unclick video' : 'This clicks'} icon={liked ? 'heart' : 'heart-outline'} selected={liked} color={liked ? theme.colors.coral : theme.colors.text} onPress={() => onClickVideo(video)} />
      <FeedIconButton label={saved ? 'Unsave video' : 'Save video'} icon={saved ? 'bookmark' : 'bookmark-outline'} selected={saved} color={saved ? theme.colors.accent : theme.colors.text} onPress={() => onSaveVideo(video)} />
      {video.source_url && <FeedIconButton label="Share original video" icon="arrow-redo-outline" onPress={() => { void Share.share({ message: video.source_url! }).catch(() => setPageError('Unable to open sharing. Please retry.')); }} />}
      {index < videos.length - 1 || nextCursor
        ? <FeedIconButton label={index < videos.length - 1 ? 'Next clip' : 'Load more clips'} icon="chevron-up" testID="next-clip" onPress={skip} />
        : <FeedIconButton label="Reload feed" icon="refresh" onPress={onReload} />}
    </View>}
    {video && <View pointerEvents="none" style={styles.progress}><View style={{ height: 3, backgroundColor: theme.colors.accent, width: `${Math.min(100, Math.max(0, player.duration ? player.currentTime / player.duration * 100 : 0))}%` }} /></View>}
    {pageError && videos.length > 0 && <Pressable accessibilityRole="button" onPress={() => pageNeedsReset ? onReload() : void fetchPage(nextCursor)} style={styles.pageError}><Text style={styles.counterText}>{pageError} {pageNeedsReset ? 'Tap to reload.' : 'Tap to retry.'}</Text></Pressable>}
  </View>;
}
const styles = StyleSheet.create({
  progress: { position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, backgroundColor: '#FFFFFF30' },
  root: { flex: 1, backgroundColor: theme.colors.background },
  touchArea: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
  center: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center', padding: 28 },
  empty: { width: '100%', maxWidth: 380, gap: 18, alignItems: 'center' },
  hint: { color: theme.colors.muted, fontFamily: theme.fonts.bold, fontSize: 12, lineHeight: 18 },
  counterText: { color: theme.colors.muted, fontFamily: theme.fonts.body, fontSize: 13 },
  pauseIcon: { height: 68, width: 68, borderRadius: 34, backgroundColor: '#09090B70', alignItems: 'center', justifyContent: 'center' },
  loadingText: { color: theme.colors.text, fontFamily: theme.fonts.body, fontSize: 13, marginTop: 14 },
  errorCard: { borderRadius: 26, backgroundColor: '#16161BF5', borderColor: theme.colors.border, borderWidth: 1, padding: 24, gap: 15, width: '100%', maxWidth: 350 },
  errorTitle: { color: theme.colors.text, fontFamily: theme.fonts.display, fontSize: 24, letterSpacing: -0.5 },
  errorText: { color: theme.colors.muted, fontFamily: theme.fonts.body, fontSize: 14, lineHeight: 21 },
  pageError: { position: 'absolute', top: 110, left: 20, right: 20, padding: 14, borderRadius: 12, backgroundColor: theme.colors.surface },
});
