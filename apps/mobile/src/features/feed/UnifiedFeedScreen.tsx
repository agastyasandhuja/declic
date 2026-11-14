import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Animated, AppState, FlatList, Image, Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { useVideoPlayer, type VideoPlayer } from 'expo-video';
import * as Crypto from 'expo-crypto';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../../state/AuthProvider';
import { ApiError } from '../../lib/api/client';
import { PlaybackRecovery, PlaybackSeek, needsPlaybackRefresh } from '../../lib/playback/PlaybackRecovery';
import { BufferedVideoViews } from '../../lib/playback/BufferedVideoViews';
import { BufferedPlayerController, type BufferedPlaybackState } from '../../lib/playback/BufferedPlayerController';
import type { PlayerDriver } from '../../lib/playback/SinglePlayerController';
import { VisibleWatchTracker, FirstFrameGuard } from '../../lib/playback/VisibleWatchTracker';
import { Ionicons } from '@expo/vector-icons';
import { PlaybackStallGuard } from '../../lib/playback/VisibleWatchTracker';
import { parseFeedPage, parsePlayback } from '../../contracts/validate';
import type { EntertainmentVideo } from '../../contracts/generated';
import { Button } from '../../components/Button';
import { sharedStyles as shared, theme } from '../../theme';
import { FeedCaption, FeedHeader, FeedIconButton, FeedScrim, feedRail } from './FeedChrome';
import { FeedProgress, FeedTouchArea, PlaybackMenu, SpeedIndicator } from './FeedControls';
import { ReelComments } from './ReelComments';
import { hasBufferHeadroom } from '../../lib/playback/MediaWarmup';
import { cachedVideoSource } from '../../lib/playback/MediaCache';
import { useMediaWarmup } from '../../lib/playback/useMediaWarmup';
import { useFeedInteraction } from './useFeedInteraction';
import { FeedQuiz, type QuizFeedback } from './FeedQuiz';
import type { PlaybackPreferences } from '../settings/ProfileScreen';
import { FeedEventBuffer } from './FeedEventBuffer';
import { seekFeedVideo } from './FeedSeek';
import { createPageReader, unifiedFeedQuery } from './paging';
import { shouldPrefetchPage } from './source';
import { appendUnified, parseUnifiedPage, type UnifiedItem } from './unified';

export function UnifiedFeedScreen({ focused, preferences, setPreferences, clickedIds, savedIds, onClickVideo, onSaveVideo, onImmersiveChange }: { onImmersiveChange?(hidden: boolean): void; focused: boolean; preferences: PlaybackPreferences; setPreferences(value: PlaybackPreferences): void; clickedIds: string[]; savedIds: string[]; onClickVideo(video: EntertainmentVideo): void; onSaveVideo(video: EntertainmentVideo): void }) {
  const { api, user } = useAuth(); const insets = useSafeAreaInsets();
  const [items, setItems] = useState<UnifiedItem[]>([]); const [index, setIndex] = useState(0); const [height, setHeight] = useState(0);
  const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  const [foreground, setForeground] = useState(AppState.currentState === 'active'); const [paused, setPaused] = useState(false);
  const [fill, setFill] = useState(false);
  const scrollY = useRef(new Animated.Value(0)).current;
  const [transitioning, setTransitioning] = useState(false);
  const [progress, setProgress] = useState({ position: 0, duration: 0 });
  const [seekBusy, setSeekBusy] = useState(false);
  const [gateAttempt, setGateAttempt] = useState(0);
  const [gateReady, setGateReady] = useState(false); const [answer, setAnswer] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<QuizFeedback | null>(null);
  const [playback, setPlayback] = useState<BufferedPlaybackState>({ loading: true, ready: false, error: null, activeSlot: 0, timedOut: false, sourceUri: null, selection: 0 });
  const [renderedSelection, setRenderedSelection] = useState<number | null>(null);
  const selectionRef = useRef(playback.selection); selectionRef.current = playback.selection;
  const firstFrame = useRef(new FirstFrameGuard()); const stalled = useRef(new PlaybackStallGuard());
  const loadAbort = useRef<AbortController | null>(null); const resumePage = useRef(false);
  const session = useRef<string | null>(null); const sessionPromise = useRef<Promise<string> | null>(null);
  const cursor = useRef<string | null>(null); const pending = useRef(false); const mounted = useRef(true);
  const generation = useRef(0); const revision = useRef<number | null>(null);
  const recovery = useRef(new PlaybackRecovery()); const resumeSeek = useRef(new PlaybackSeek());
  const terminal = useRef(new Set<string>()); const retryingVideo = useRef<string | null>(null);
  const itemRef = useRef<UnifiedItem | undefined>(undefined); const indexRef = useRef(0); indexRef.current = index;
  const heightRef = useRef(height); heightRef.current = height;
  const list = useRef<FlatList<UnifiedItem>>(null); const values = useRef(items); values.current = items;
  const events = useMemo(() => new FeedEventBuffer(api), [api]);
  const watch = useRef(new VisibleWatchTracker()); const answerKey = useRef(Crypto.randomUUID()); const submittedAnswer = useRef<string | null>(null);
  const setup = (p: VideoPlayer) => { p.loop = true; p.staysActiveInBackground = false; p.audioMixingMode = 'doNotMix'; p.bufferOptions = { preferredForwardBufferDuration: 5, waitsToMinimizeStalling: false }; };
  const first = useVideoPlayer(null, setup); const second = useVideoPlayer(null, setup);
  const controller = useMemo(() => new BufferedPlayerController([first, second].map(p => ({ play: () => p.play(), pause: () => p.pause(), setRate: (rate: number) => { if (p.playbackRate !== rate) p.playbackRate = rate; }, setMuted: (muted: boolean) => { p.muted = muted; }, seekTo: (seconds: number) => { p.currentTime = seconds; }, replaceAsync: (uri: string | null) => p.replaceAsync(cachedVideoSource(uri)) })) as [PlayerDriver, PlayerDriver], setPlayback), [first, second]);
  const player = playback.activeSlot === 0 ? first : second;
  const visibility = useRef({ focused, foreground }); visibility.current = { focused, foreground };
  const current = items[index]; itemRef.current = current;
  const video = current && current.kind !== 'quiz' ? current.video : null;
  const { interaction, state: gesture, playbackBlocked: gesturePlaybackBlocked, scrollBlocked } = useFeedInteraction(video ? current!.item_id : null, focused && foreground, rate => controller.setRate(rate), onImmersiveChange, preferences.reducedMotion);
  const playbackBlocked = gesturePlaybackBlocked || seekBusy;
  const sourceReady = !!video && playback.ready && playback.sourceUri === video.playback.url;
  const frameRendered = renderedSelection === playback.selection;
  const previous = items[index - 1]; const previousUrl = previous && previous.kind !== 'quiz' ? previous.video.playback.url : undefined;
  const next = items[index + 1]; const nextUrl = next && next.kind !== 'quiz' ? next.video.playback.url : undefined;
  const immediateReady = !!nextUrl && !!playback.buffers?.some(buffer => buffer.uri === nextUrl && buffer.ready);
  const warmAssets = items.slice(index + 2, index + 8).flatMap(item => item.kind === 'quiz' ? [] : [item.video.playback]);
  const standby = playback.activeSlot === 0 ? second : first;
  useMediaWarmup(warmAssets, hasBufferHeadroom(player.bufferedPosition, player.currentTime, player.duration) && hasBufferHeadroom(standby.bufferedPosition, 0, standby.duration) && sourceReady && frameRendered && immediateReady && focused && foreground && !transitioning && !playbackBlocked);
  const emit = useCallback((type: string, position = 0, watched = 0, item = itemRef.current) => {
    if (!session.current || !item || item.kind === 'quiz' || terminal.current.has(item.item_id)) return;
    if (resumeSeek.current.isPending(item.item_id)) {
      if (type === 'playback_progress') return;
      position = resumeSeek.current.anchor(item.item_id, position);
    }
    events.add({ event_id: Crypto.randomUUID(), session_id: session.current, item_id: item.item_id,
      event_type: type, client_occurred_at: new Date().toISOString(), payload: { position_ms: Math.max(0, Math.round(position)), visible_watch_ms: Math.max(0, Math.round(watched)) } });
  }, [events]);
  const flush = useCallback(async () => { try { await events.flush(); } catch { /* Retry the same IDs in chronological order. */ } }, [events]);
  const ensureSession = useCallback(async () => {
    if (session.current) return session.current;
    if (!sessionPromise.current) sessionPromise.current = api.request<{session_id: string}>('/v1/feed/sessions', { method: 'POST', body: { refresh_unseen: true }, headers: { 'Idempotency-Key': Crypto.randomUUID() } }).then(r => { session.current = r.session_id; return r.session_id; }).finally(() => { sessionPromise.current = null; });
    return sessionPromise.current;
  }, [api]);
  const load = useCallback(async (reset = false) => {
    if (pending.current && !reset) return; const request = ++generation.current; loadAbort.current?.abort(); const abort = new AbortController(); loadAbort.current = abort; pending.current = true; setLoading(true); setError(null);
    try {
      const id = await ensureSession(); await flush();
      if (generation.current !== request || abort.signal.aborted) return;
      if (reset && itemRef.current?.kind !== 'quiz' && values.current.length) {
        const refreshed = await api.request<{session_id: string}>('/v1/feed/sessions', { method: 'POST', body: { resume_session_id: id, refresh_unseen: true }, headers: { 'Idempotency-Key': Crypto.randomUUID() } });
        if (refreshed.session_id !== id) throw new Error('Your feed session changed. Please reopen the feed.');
      }
      const query = unifiedFeedQuery(id, reset ? null : cursor.current);
      const pacedRead = createPageReader(abort.signal);
      const read = () => pacedRead(async () => parseUnifiedPage(await api.request(`/v1/feed?${query}`, { signal: abort.signal })));
      const available = (page: ReturnType<typeof parseUnifiedPage>) => page.items.some(item => reset || !values.current.some(previous => previous.item_id === item.item_id));
      let page = await read();
      const seen = new Set(query.has('cursor') ? [query.get('cursor')!] : []);
      for (let skipped = 0; !available(page) && page.next_cursor && skipped < 3; skipped++) {
        if (seen.has(page.next_cursor)) throw new Error('The feed repeated a page. Please refresh.');
        seen.add(page.next_cursor);
        if (generation.current !== request || abort.signal.aborted) return;
        cursor.current = page.next_cursor;
        query.set('cursor', page.next_cursor);
        page = await read();
      }
      if (!mounted.current || generation.current !== request || abort.signal.aborted) return;
      if (page.next_cursor && seen.has(page.next_cursor)) throw new Error('The feed repeated a page. Please refresh.');
      if (page.session_id !== id) throw new Error('Feed session changed. Please reload.');
      if (!reset && revision.current !== null && revision.current !== page.recommendation_revision) {
        cursor.current = null;
        throw new Error('Your feed has updated. Tap Retry to load your next clips.');
      }
      revision.current = page.recommendation_revision;
      cursor.current = page.next_cursor;
      if (!available(page) && page.next_cursor) throw new Error('No new videos are ready in this window. Retry shortly.');
      const merged = reset ? page.items : appendUnified(values.current, page.items);
      const remove = reset ? 0 : Math.min(Math.max(0, merged.length - 80), Math.max(0, indexRef.current - 10));
      values.current = merged.slice(remove); setItems(values.current);
      if (remove) { setIndex(indexRef.current - remove); list.current?.scrollToOffset({ offset: (indexRef.current - remove) * heightRef.current, animated: false }); }
      if (reset) { indexRef.current = 0; setIndex(0); list.current?.scrollToOffset({ offset: 0, animated: false }); }
    } catch (problem) { if (mounted.current && generation.current === request && !abort.signal.aborted) { if (problem instanceof ApiError && problem.code === 'STALE_CURSOR') cursor.current = null; setError(problem instanceof Error ? problem.message : 'Unable to load your feed.'); } }
    finally { if (generation.current === request) { pending.current = false; if (mounted.current) setLoading(false); } }
  }, [api, ensureSession, flush]);
  useEffect(() => { mounted.current = true; void load(true); return () => { mounted.current = false; generation.current++; loadAbort.current?.abort(); void flush(); }; }, [load, flush]);
  useEffect(() => {
    if (!focused || !foreground) {
      if (pending.current) { resumePage.current = true; loadAbort.current?.abort(); }
    } else if (resumePage.current && !loading) {
      resumePage.current = false; void load();
    }
  }, [focused, foreground, loading, load]);
  useLayoutEffect(() => () => controller.dispose(), [controller]);
  useLayoutEffect(() => {
    recovery.current.observe(video ? current!.item_id : null, focused && foreground);
    controller.setGate({ focused: focused && !!video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== current?.item_id, foreground, manuallyPaused: paused || playbackBlocked });
  }, [controller, focused, foreground, paused, playbackBlocked, current?.item_id, video?.playback.expires_at, !!video]);
  useLayoutEffect(() => { controller.setMuted(preferences.muted); }, [controller, preferences.muted]);
  useEffect(() => {
    const listeners = [first, second].map((p, slot) => p.addListener('playingChange', event => { if (event.isPlaying) controller.enforcePlaybackOwner(slot as 0 | 1); }));
    return () => listeners.forEach(listener => listener.remove());
  }, [controller, first, second]);
  useEffect(() => { const subscription = AppState.addEventListener('change', state => { const active = state === 'active'; if (!active) interaction.reset(); visibility.current.foreground = active; const selected = itemRef.current; const stale = selected && selected.kind !== 'quiz' && needsPlaybackRefresh(selected.video.playback.expires_at); controller.setGate({ foreground: active, ...(active && stale ? { focused: false } : {}) }); setForeground(active); emit(active ? 'app_foregrounded' : 'app_backgrounded', player.currentTime * 1000, watch.current.totalMs); if (active) emit('playback_started', player.currentTime * 1000, watch.current.totalMs); void flush(); }); return () => subscription.remove(); }, [controller, player, emit, flush]);
  useEffect(() => {
    resumeSeek.current.clear(); setProgress({ position: 0, duration: 0 });
    watch.current = new VisibleWatchTracker(); stalled.current = new PlaybackStallGuard(); setPaused(false); setAnswer(null); setFeedback(null); setGateReady(false); answerKey.current = Crypto.randomUUID(); submittedAnswer.current = null;
    if (video) emit('playback_started');
  }, [current?.item_id, emit]);
  useEffect(() => {
    if (video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== current?.item_id) void controller.setSelection(video.playback.url);
  }, [current?.item_id, video?.playback.url, controller]);
  useEffect(() => {
    if (video && current && focused && foreground && (needsPlaybackRefresh(video.playback.expires_at) || (playback.error && playback.sourceUri === video.playback.url)) && recovery.current.claim(current.item_id)) void retryVideo();
  }, [current?.item_id, focused, foreground, video?.playback.expires_at, video?.playback.url, playback.error, playback.sourceUri]);
  // React has now attached the selected surface; reapply the existing playback gates.
  useEffect(() => { if (sourceReady) controller.setGate({}); }, [controller, sourceReady, playback.selection]);
  // Give the visible clip its first frame before competing for bandwidth.
  useEffect(() => { if (sourceReady && frameRendered && focused && foreground && !transitioning) controller.preload(nextUrl); }, [controller, sourceReady, frameRendered, focused, foreground, transitioning, nextUrl]);
  useEffect(() => {
    if (!video) return;
    let ticks = 0;
    const enabled = focused && foreground && !paused && !playbackBlocked && sourceReady;
    firstFrame.current.sample(playback.selection, frameRendered, Date.now(), enabled);
    stalled.current.sample(player.currentTime * 1000, Date.now(), enabled);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    const timer = setInterval(() => {
      const position = player.currentTime * 1000;
      setProgress(sourceReady ? { position: player.currentTime, duration: player.duration } : { position: 0, duration: 0 });
      if (playbackBlocked) { watch.current.sample(position, Date.now(), false); return; }
      if (stalled.current.sample(position, Date.now(), enabled) || firstFrame.current.sample(playback.selection, frameRendered, Date.now(), enabled)) controller.reportError(true);
      if (sourceReady && player.status === 'error') controller.reportError();
      if (current && resumeSeek.current.isPending(current.item_id)) {
        const settled = resumeSeek.current.settled(current.item_id, position, player.duration * 1000, Date.now());
        watch.current.sample(position, Date.now(), false);
        if (settled === 'timeout' && sourceReady) controller.reportError(true);
        return; // Seeking never contributes progress or visible watch time.
      }
      const total = watch.current.sample(position, Date.now(), enabled && !gesture.comments && frameRendered && player.playing && player.status === 'readyToPlay', player.duration * 1000, gesture.speed);
      if (++ticks % 6 === 0) { emit('playback_progress', position, total); void flush(); }
    }, 500);
    return () => clearInterval(timer);
  }, [current?.item_id, player, focused, foreground, paused, playbackBlocked, gesture.speed, gesture.comments, sourceReady, playback.selection, frameRendered, emit, flush]);
  useEffect(() => { if (shouldPrefetchPage({ index, count: items.length, hasNext: !!cursor.current, focused: focused && sourceReady && frameRendered, foreground, loading, hasError: !!error }) && items.at(-1)?.kind !== 'quiz') void load(); }, [index, items, focused, foreground, loading, error, load, sourceReady, frameRendered]);
  useEffect(() => {
    if (!focused || !foreground || items.length) return;
    const timer = setInterval(() => { if (!pending.current) void load(); }, 10000);
    return () => clearInterval(timer);
  }, [focused, foreground, items.length, load]);
  useEffect(() => { if (!focused || !foreground || current?.kind !== 'quiz') return; let cancelled = false;
    events.flush().then(() => api.request<{scroll_locked: boolean}>(`/v1/feed/sessions/${session.current}/quiz-gate`, { method: 'POST', headers: { 'Idempotency-Key': current.item_id }, body: { item_id: current.item_id, quiz_instance_id: current.quiz.quiz_instance_id } })).then(result => { if (!cancelled) { setGateReady(result.scroll_locked); if (!result.scroll_locked) void load(true); } }).catch(problem => { if (!cancelled) setError(problem.message); });
    return () => { cancelled = true; };
  }, [current?.item_id, focused, foreground, api, load, events, gateAttempt]);
  const move = useRef((nextIndex: number) => {});
  move.current = nextIndex => { if (nextIndex === indexRef.current || itemRef.current?.kind === 'quiz') return; interaction.reset(); emit('video_skipped', player.currentTime * 1000, watch.current.totalMs); if (itemRef.current) terminal.current.add(itemRef.current.item_id); void flush(); controller.setGate({ focused: false }); indexRef.current = nextIndex; setIndex(nextIndex); };
  const viewable = useRef(({ viewableItems }: { viewableItems: { index?: number | null }[] }) => { const i = viewableItems[0]?.index; if (i != null) move.current(i); }).current;
  async function submit() {
    if (current?.kind !== 'quiz' || !answer || !gateReady || busy) return;
    setBusy(true); setError(null); submittedAnswer.current ??= answer;
    try { const result = await api.request<QuizFeedback & { scroll_unlocked: boolean }>(`/v1/quizzes/${current.quiz.quiz_instance_id}/answers`, { method: 'POST', headers: { 'Idempotency-Key': answerKey.current }, body: { session_id: session.current, selected_option_id: submittedAnswer.current } }); if (!result.scroll_unlocked) throw new Error('Please retry your answer.'); setFeedback({ correct: result.correct, explanation: result.explanation }); cursor.current = null; }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'Answer not sent. Retry.'); } finally { setBusy(false); }
  }
  async function recoverQuiz() {
    if (current?.kind !== 'quiz' || !gateReady || busy) return;
    setBusy(true);
    try { await api.request(`/v1/quizzes/${current.quiz.quiz_instance_id}/recover`, { method: 'POST', headers: { 'Idempotency-Key': answerKey.current + '-recover' }, body: { session_id: session.current, reason: 'submission_unavailable', client_event_id: answerKey.current + '-recover' } }); cursor.current = null; await load(true); }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'Please retry when connected.'); } finally { setBusy(false); }
  }
  function socialAction(action: (video: EntertainmentVideo) => void) {
    if (current?.kind !== 'entertainment_video') return;
    try { action(parseFeedPage({ schema_version: '1', items: [current.video], next_cursor: null }).items[0]); }
    catch { setError('This clip cannot be saved. Refresh and try again.'); }
  }
  async function retryVideo() {
    if (!video || !current || current.kind === 'quiz' || retryingVideo.current === current.item_id) return;
    const itemId = current.item_id; retryingVideo.current = itemId; setError(null);
    resumeSeek.current.capture(itemId, player.currentTime * 1000, playback.selection);
    controller.setGate({ focused: false }); setRenderedSelection(null);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    try {
      const route = current.kind === 'study_video' ? 'learning' : 'entertainment';
      const fresh = parsePlayback(await api.request(`/v1/${route}/videos/${video.video_id}/playback`));
      if (!mounted.current || itemRef.current?.item_id !== itemId) return;
      if (needsPlaybackRefresh(fresh.expires_at)) throw new Error('The refreshed video link has expired. Retry shortly.');
      setItems(old => old.map(item => item.item_id === itemId && item.kind !== 'quiz' ? { ...item, video: { ...item.video, playback: fresh } } : item));
      await controller.setSelection(fresh.url, undefined, true);
      if (mounted.current && itemRef.current?.item_id === itemId) controller.setGate({ focused: visibility.current.focused && visibility.current.foreground });
    } catch (problem) { if (mounted.current && itemRef.current?.item_id === itemId) { controller.reportError(); setError(problem instanceof Error ? problem.message : 'This video is unavailable.'); } }
    finally { if (retryingVideo.current === itemId) retryingVideo.current = null; }
  }
  const entertainment = current?.kind === 'entertainment_video' ? current.video : null;
  const liked = !!entertainment && clickedIds.includes(entertainment.video_id);
  const saved = !!entertainment && savedIds.includes(entertainment.video_id);
  const showMore = !!video && index === items.length - 1;

  function onFrame(selection: number) {
    if (selectionRef.current !== selection) return;
    const id = itemRef.current?.item_id;
    const target = id ? resumeSeek.current.takeTarget(id, selection, Date.now()) : null;
    if (target !== null) { controller.seekTo(target / 1000); watch.current.sample(target, Date.now(), false); }
    setRenderedSelection(selection);
  }
  function beginScrub() {
    if (!video || !current || current.kind === 'quiz') return;
    emit('playback_progress', player.currentTime * 1000, watch.current.totalMs);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    interaction.scrub(true); controller.setGate({ manuallyPaused: true });
  }
  async function seek(seconds: number) {
    if (!video || !current || current.kind === 'quiz' || !session.current) return;
    const itemId = current.item_id; setSeekBusy(true); setError(null);
    try {
      await seekFeedVideo({ api, events, sessionId: session.current, itemId, eventId: Crypto.randomUUID(), positionMs: seconds * 1000, visibleWatchMs: watch.current.totalMs,
        isActive: () => itemRef.current?.item_id === itemId && visibility.current.foreground && visibility.current.focused,
        isCurrent: () => mounted.current && itemRef.current?.item_id === itemId,
        onSeek: () => { controller.seekTo(seconds); watch.current.sample(seconds * 1000, Date.now(), false); setProgress({ position: seconds, duration: player.duration }); },
      });
    } catch (problem) { if (itemRef.current?.item_id === itemId) setError(problem instanceof Error ? problem.message : 'Unable to seek. Try again.'); }
    finally { setSeekBusy(false); }
  }
  return (
    <View style={styles.screen} onLayout={event => setHeight(event.nativeEvent.layout.height)}>
      <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, !preferences.reducedMotion && { transform: [{ translateY: Animated.add(Animated.multiply(scrollY, -1), index * height) }] }]}><BufferedVideoViews players={[first, second]} playback={playback} sourceReady={sourceReady} visible={!!video} fill={fill} onFrame={onFrame} adjacent={{ height, nextUrl, previousUrl }} /></Animated.View>
      {height > 0 && items.length > 0 ? (
        <Animated.FlatList
          ref={list}
          data={items}
          extraData={[index, answer, feedback, gateReady, busy, error, paused, gesture.hidden, preferences.captions]}
          removeClippedSubviews={false}
          initialNumToRender={2}
          maxToRenderPerBatch={2}
          windowSize={3}
          keyExtractor={item => item.item_id}
          pagingEnabled
          snapToInterval={height}
          decelerationRate="fast"
          disableIntervalMomentum
          bounces={false}
          scrollEventThrottle={16}
          onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], { useNativeDriver: true })}
          onScrollBeginDrag={() => { interaction.reset(); setTransitioning(true); }} onMomentumScrollEnd={() => setTransitioning(false)} onScrollEndDrag={event => { const y = event.nativeEvent.contentOffset.y; if (height > 0 && Math.abs(y - Math.round(y / height) * height) < 1) setTransitioning(false); }}
          scrollEnabled={current?.kind !== 'quiz' && !scrollBlocked && !seekBusy}
          showsVerticalScrollIndicator={false}
          getItemLayout={(_, i) => ({ length: height, offset: i * height, index: i })}
          viewabilityConfig={{ itemVisiblePercentThreshold: 80 }}
          onViewableItemsChanged={viewable}
          renderItem={({ item, index: cardIndex }) => (
            <View style={{ height }}>
              {item.kind === 'quiz' ? (
                <FeedQuiz
                  quiz={item.quiz}
                  top={insets.top + 76}
                  answer={answer}
                  feedback={feedback}
                  busy={busy}
                  ready={gateReady}
                  answerSent={submittedAnswer.current !== null}
                  error={error}
                  onSelect={setAnswer}
                  onSubmit={() => void submit()}
                  onContinue={() => void load(true)}
                  onRecover={() => void recoverQuiz()}
                  onRetry={() => { setError(null); setGateAttempt(n => n + 1); }}
                />
              ) : (
                <>
                  {(cardIndex !== index || !sourceReady || !frameRendered) && item.video.thumbnail_url && (cardIndex === index || !playback.buffers?.some(buffer => buffer.uri === item.video.playback.url && buffer.ready)) && <Image source={{ uri: item.video.thumbnail_url }} resizeMode={fill ? 'cover' : 'contain'} style={StyleSheet.absoluteFill} />}
                  {!gesture.hidden && <FeedScrim />}
                  {cardIndex === index && <FeedTouchArea interaction={interaction} paused={paused} error={!!playback.error} onToggle={() => setPaused(value => !value)} />}
                  {!gesture.hidden && <FeedCaption
                    byline={item.kind === 'study_video' ? item.course_context?.title : item.video.creator?.display_name || item.video.creator?.handle}
                    title={item.video.title}
                    caption={preferences.captions ? item.video.caption || item.reason_text : undefined}
                  />}
                </>
              )}
            </View>
          )}
        />
      ) : (
        <View style={styles.empty}>
          <Ionicons name="play-circle-outline" size={46} color={theme.colors.accent} />
          <Text style={styles.emptyTitle}>{loading ? 'Loading your feed' : 'Your feed is getting ready'}</Text>
          {loading ? <ActivityIndicator color={theme.colors.accent} /> : (
            <>
              <Text style={styles.emptyText}>Manage your connections in Courses, then refresh for new videos.</Text>
              <Button title="Refresh feed" onPress={() => void load(true)} />
            </>
          )}
        </View>
      )}

      {video && !gesture.hidden && (
        <View pointerEvents="box-none" style={feedRail}>
          {entertainment && (
            <>
              <FeedIconButton reducedMotion={preferences.reducedMotion} count={video?.like_count} label={liked ? 'Unclick video' : 'This clicks'} icon={liked ? 'heart' : 'heart-outline'} selected={liked} color={liked ? theme.colors.coral : theme.colors.text} onPress={() => socialAction(onClickVideo)} />
              <FeedIconButton reducedMotion={preferences.reducedMotion} count={video?.comment_count} label="Comments" icon="chatbubble-ellipses-outline" onPress={() => interaction.openComments()} />
              <FeedIconButton reducedMotion={preferences.reducedMotion} label={saved ? 'Unsave video' : 'Save video'} icon={saved ? 'bookmark' : 'bookmark-outline'} selected={saved} color={saved ? theme.colors.accent : theme.colors.text} onPress={() => socialAction(onSaveVideo)} />
              {entertainment.source_url && <FeedIconButton reducedMotion={preferences.reducedMotion} label="Open original post" icon="open-outline" onPress={() => socialAction(clip => { if (clip.source_url) void Linking.openURL(clip.source_url).catch(() => setError('Unable to open this post.')); })} />}
            </>
          )}
          {index + 1 < items.length && (
            <FeedIconButton reducedMotion={preferences.reducedMotion} label={items[index + 1].kind === 'quiz' ? 'Next question' : 'Next video'} icon="chevron-up" onPress={() => { move.current(index + 1); list.current?.scrollToIndex({ index: index + 1, animated: !preferences.reducedMotion }); }} />
          )}
          {showMore && <FeedIconButton reducedMotion={preferences.reducedMotion} label={loading ? 'Loading videos' : 'More videos'} icon="refresh" disabled={loading} onPress={() => void load(!cursor.current)} />}
        </View>
      )}

      {!gesture.hidden && <FeedHeader top={insets.top + 8} />}
      {video && !gesture.hidden && <FeedProgress key={current?.item_id} position={progress.position} duration={progress.duration} disabled={!focused || !foreground || !sourceReady || !frameRendered || seekBusy || resumeSeek.current.isPending(current!.item_id)} onBegin={beginScrub} onSeek={seek} onEnd={() => { if (itemRef.current?.item_id === current?.item_id) interaction.scrub(false); }} />}
      <SpeedIndicator visible={gesture.speed === 2} />
    <PlaybackMenu open={gesture.menu} onClose={() => interaction.closeOverlay()} muted={preferences.muted} fill={fill} captions={preferences.captions} onMute={() => setPreferences({ ...preferences, muted: !preferences.muted })} onFill={() => setFill(value => !value)} onCaptions={() => setPreferences({ ...preferences, captions: !preferences.captions })} onRefresh={() => void load(true)} />
      <ReelComments owner={user?.user_id ?? null} count={video?.comment_count} warm={focused && foreground && sourceReady && frameRendered && !transitioning && hasBufferHeadroom(player.bufferedPosition, player.currentTime, player.duration) && (!nextUrl || (immediateReady && hasBufferHeadroom(standby.bufferedPosition, 0, standby.duration)))} open={gesture.comments} videoId={entertainment?.video_id ?? null} enabled={!!entertainment} api={api} onClose={() => interaction.closeOverlay()} />
      {video && !gesture.hidden && (!sourceReady || !frameRendered || playback.error) && (
        <View pointerEvents="box-none" style={styles.playback}>
          {playback.error ? <Button title="Retry video" onPress={() => void retryVideo()} /> : <ActivityIndicator color={theme.colors.accent} />}
        </View>
      )}
      {error && !gesture.hidden && current?.kind !== 'quiz' && (
        <View style={[styles.error, { top: insets.top + 64 }]}>
          <Text accessibilityRole="alert" style={shared.subtitle}>{error}</Text>
          <Button title="Retry" secondary onPress={() => void load(!cursor.current)} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, overflow: 'hidden', backgroundColor: theme.colors.background },
  playArea: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
  playIcon: { width: 68, height: 68, borderRadius: 34, alignItems: 'center', justifyContent: 'center', backgroundColor: '#09090B70' },
  empty: { flex: 1, width: '100%', maxWidth: 380, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', padding: 26, gap: 16 },
  emptyTitle: { fontFamily: theme.fonts.display, color: theme.colors.text, fontSize: 24, lineHeight: 28, textAlign: 'center' },
  emptyText: { fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 15, lineHeight: 22, textAlign: 'center' },
  playback: { position: 'absolute', top: '45%', alignSelf: 'center' },
  error: { position: 'absolute', left: 20, right: 20, padding: 16, gap: 8, backgroundColor: theme.colors.surface, borderRadius: 16 },
});
