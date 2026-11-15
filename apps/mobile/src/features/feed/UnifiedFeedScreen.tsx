import { startupTrace } from '../../lib/playback/startupMetrics';
import { config } from '../../config';
import { feedBootstrap } from './startup';
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Animated, AppState, FlatList, Image, Share, Pressable, StyleSheet, Text, View } from 'react-native';
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
import { FeedPlaybackWake, FeedProgress, FeedTouchArea, PlaybackMenu, SpeedIndicator } from './FeedControls';
import { ReelComments } from './ReelComments';
import { hasBufferHeadroom } from '../../lib/playback/MediaWarmup';
import { cachedVideoSource, discardCachedVideo, releaseCachedVideo } from '../../lib/playback/MediaCache';
import { useMediaWarmup } from '../../lib/playback/useMediaWarmup';
import { createExpoPlayerDriver } from '../../lib/playback/ExpoPlayerDriver';
import { useFeedInteraction } from './useFeedInteraction';
import { useUpcomingPlayback } from './useUpcomingPlayback';
import { isUnavailablePlayback, updateUpcomingPlayback } from './upcomingPlayback';
import { FeedQuiz, type QuizFeedback } from './FeedQuiz';
import type { PlaybackPreferences } from '../settings/ProfileScreen';
import { FeedEventBuffer } from './FeedEventBuffer';
import { seekFeedVideo, waitForNativeSeek } from './FeedSeek';
import { createPageReader, unifiedFeedQuery } from './paging';
import { shouldPrefetchPage } from './source';
import { appendUnified, parseUnifiedPage, studyCourseLabel, type UnifiedItem, type UnifiedVideo } from './unified';

export function UnifiedFeedScreen({ focused, preferences, setPreferences, clickedIds, savedIds, onClickVideo, onSaveVideo, onImmersiveChange }: { onImmersiveChange?(hidden: boolean): void; focused: boolean; preferences: PlaybackPreferences; setPreferences(value: PlaybackPreferences): void; clickedIds: string[]; savedIds: string[]; onClickVideo(video: EntertainmentVideo): void; onSaveVideo(video: EntertainmentVideo): void }) {
  const { api, user } = useAuth(); const insets = useSafeAreaInsets();
  const [items, setItems] = useState<UnifiedItem[]>([]); const [index, setIndex] = useState(0); const [height, setHeight] = useState(0);
  const [listRevision, setListRevision] = useState(0);
  const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  const [foreground, setForeground] = useState(AppState.currentState === 'active'); const [paused, setPaused] = useState(false);
  const [fill, setFill] = useState(false);
  const scrollY = useRef(new Animated.Value(0)).current;
  const [transitioning, setTransitioning] = useState(false);
  const [progress, setProgress] = useState({ position: 0, duration: 0 });
  const [seekBusy, setSeekBusy] = useState(false);
  const seekAnchor = useRef<{ itemId: string; positionMs: number; settling: boolean } | null>(null);
  const [gateAttempt, setGateAttempt] = useState(0);
  const [gateReady, setGateReady] = useState(false); const [answer, setAnswer] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<QuizFeedback | null>(null);
  const [playback, setPlayback] = useState<BufferedPlaybackState>({ loading: true, ready: false, error: null, activeSlot: 0, timedOut: false, sourceUri: null, selection: 0 });
  const [renderedSelection, setRenderedSelection] = useState<number | null>(null);
  const selectionRef = useRef(playback.selection); selectionRef.current = playback.selection;
  const firstFrame = useRef(new FirstFrameGuard()); const stalled = useRef(new PlaybackStallGuard());
  const loadAbort = useRef<AbortController | null>(null);
  const requestResetsFeed = useRef(false);
  const resumePage = useRef<boolean | null>(null);
  const presentation = useRef(false);
  const startupPage = useRef<ReturnType<typeof parseUnifiedPage> | null>(null);
  const session = useRef<string | null>(null); const sessionPromise = useRef<Promise<string> | null>(null);
  const cursor = useRef<string | null>(null); const pending = useRef(false); const mounted = useRef(true);
  const generation = useRef(0); const revision = useRef<number | null>(null);
  const recovery = useRef(new PlaybackRecovery()); const resumeSeek = useRef(new PlaybackSeek());
  const terminal = useRef(new Set<string>()); const retryingVideo = useRef<string | null>(null);
  const unavailableVideos = useRef(new Set<string>());
  const itemRef = useRef<UnifiedItem | undefined>(undefined); const indexRef = useRef(0); indexRef.current = index;
  const heightRef = useRef(height); heightRef.current = height;
  const list = useRef<FlatList<UnifiedItem>>(null); const values = useRef(items); values.current = items;
  const events = useMemo(() => new FeedEventBuffer(api), [api]);
  const watch = useRef(new VisibleWatchTracker()); const answerKey = useRef(Crypto.randomUUID()); const submittedAnswer = useRef<string | null>(null);
  const setup = (p: VideoPlayer) => { p.loop = true; p.staysActiveInBackground = false; p.audioMixingMode = 'doNotMix'; p.bufferOptions = { preferredForwardBufferDuration: 10, waitsToMinimizeStalling: false }; };
  const first = useVideoPlayer(null, setup); const second = useVideoPlayer(null, setup);
  const controller = useMemo(() => new BufferedPlayerController([first, second].map(p => createExpoPlayerDriver(p, cachedVideoSource, discardCachedVideo, releaseCachedVideo)) as [PlayerDriver, PlayerDriver], setPlayback), [first, second]);
  const player = playback.activeSlot === 0 ? first : second;
  const visibility = useRef({ focused, foreground }); visibility.current = { focused, foreground };
  const current = items[index]; itemRef.current = current;
  const video = current && current.kind !== 'quiz' ? current.video : null;
  const { interaction, state: gesture, playbackBlocked: gesturePlaybackBlocked, scrollBlocked } = useFeedInteraction(video ? current!.item_id : null, focused && foreground, rate => controller.setRate(rate), onImmersiveChange, preferences.reducedMotion);
  const playbackBlocked = gesturePlaybackBlocked || seekBusy;
  const sourceReady = !!video && playback.ready && playback.sourceUri === video.playback.url;
  const frameRendered = renderedSelection === playback.selection;
  const previous = items[index - 1]; const previousUrl = previous && previous.kind !== 'quiz' ? previous.video.playback.url : undefined;
  const following = items[index + 1];
  const next = following?.kind === 'quiz' ? undefined : following;
  const nextUrl = next?.video.playback.url;
  const immediateReady = !!nextUrl && !!playback.buffers?.some(buffer => buffer.uri === nextUrl && buffer.ready);
  const standby = playback.activeSlot === 0 ? second : first;
  const warmStart = index + (presentation.current ? 1 : 2);
  const upcoming = items.slice(warmStart, warmStart + 6);
  const quizBoundary = upcoming.findIndex(item => item.kind === 'quiz');
  const warmAssets = upcoming.slice(0, quizBoundary < 0 ? undefined : quizBoundary)
    .flatMap(item => item.kind === 'quiz' ? [] : [{ ...item.video.playback, ...(item.kind === 'entertainment_video' ? { video_id: item.video.video_id } : {}) }]);
  if (presentation.current && video) warmAssets.push(video.playback);
  const standbyBuffered = !nextUrl || (immediateReady && hasBufferHeadroom(standby.bufferedPosition, 0, standby.duration));
  useMediaWarmup(warmAssets, hasBufferHeadroom(player.bufferedPosition, player.currentTime, player.duration) && standbyBuffered && sourceReady && frameRendered && focused && foreground && !transitioning && !playbackBlocked);
  const emit = useCallback((type: string, position = 0, watched = 0, item = itemRef.current) => {
    if (!session.current || !item || item.kind === 'quiz' || terminal.current.has(item.item_id)) return;
    const anchor = seekAnchor.current;
    if (anchor?.itemId === item.item_id) {
      if (type === 'playback_progress' && anchor.settling) return;
      // AVPlayer can land a few frames behind the requested time.
      if (anchor.settling || position < anchor.positionMs) position = anchor.positionMs;
      else seekAnchor.current = null;
    }
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
    if (!sessionPromise.current) sessionPromise.current = feedBootstrap.take(`${config.apiBaseUrl}:${user?.user_id}`, api).then(page => { startupPage.current = page; session.current = page.session_id; return page.session_id; }).finally(() => { sessionPromise.current = null; });
    return sessionPromise.current;
  }, [api, user?.user_id]);
  const load = useCallback(async (reset = false) => {
    if (pending.current && !reset) return; const request = ++generation.current; loadAbort.current?.abort(); const abort = new AbortController(); loadAbort.current = abort; pending.current = true; setLoading(true); setError(null);
    requestResetsFeed.current = reset;
    if (reset) unavailableVideos.current.clear();
    try {
      await flush();
      if (generation.current !== request || abort.signal.aborted) return;
      const pacedRead = createPageReader(abort.signal);
      const id = await ensureSession();
      if (generation.current !== request || abort.signal.aborted) return;
      const firstPage = startupPage.current;
      if (!firstPage && reset && itemRef.current?.kind !== 'quiz' && values.current.length) {
        const refreshed = await api.request<{session_id: string}>('/v1/feed/sessions', { method: 'POST', body: { resume_session_id: id, refresh_unseen: true }, headers: { 'Idempotency-Key': Crypto.randomUUID() } });
        if (refreshed.session_id !== id) throw new Error('Your feed session changed. Please reopen the feed.');
      }
      const query = unifiedFeedQuery(id, reset ? null : cursor.current);
      const read = () => pacedRead(async () => parseUnifiedPage(await api.request(`/v1/feed?${query}`, { signal: abort.signal })));
      const availableItems = (page: ReturnType<typeof parseUnifiedPage>) => page.items.filter(item => item.kind === 'quiz' || !unavailableVideos.current.has(item.video.video_id));
      const available = (page: ReturnType<typeof parseUnifiedPage>) => availableItems(page).some(item => reset || !values.current.some(previous => previous.item_id === item.item_id));
      let page = firstPage ?? await read();
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
      if (page.demo_mode !== undefined) presentation.current = page.demo_mode;
      startupPage.current = null;
      revision.current = page.recommendation_revision;
      cursor.current = page.next_cursor;
      if (!available(page) && page.next_cursor) throw new Error('No new videos are ready in this window. Retry shortly.');
      const incoming = availableItems(page);
      const merged = reset ? incoming : appendUnified(values.current, incoming);
      const remove = reset ? 0 : Math.min(Math.max(0, merged.length - 80), Math.max(0, indexRef.current - 10));
      values.current = merged.slice(remove); setItems(values.current);
      if (remove) { setIndex(indexRef.current - remove); list.current?.scrollToOffset({ offset: (indexRef.current - remove) * heightRef.current, animated: false }); }
      if (reset) {
        // Mount the replacement page at its first row. The existing native list
        // still has the quiz page's dimensions and scroll lock at this point.
        indexRef.current = 0;
        setIndex(0);
        setTransitioning(false);
        scrollY.setValue(0);
        setListRevision(request);
      }
    } catch (problem) { if (mounted.current && generation.current === request && !abort.signal.aborted) { if (problem instanceof ApiError && problem.code === 'STALE_CURSOR') cursor.current = null; setError(problem instanceof Error ? problem.message : 'Unable to load your feed.'); } }
    finally { if (generation.current === request) { pending.current = false; if (mounted.current) setLoading(false); } }
  }, [api, ensureSession, flush, scrollY]);
  useEffect(() => { mounted.current = true; void load(true); return () => { mounted.current = false; generation.current++; loadAbort.current?.abort(); void flush(); }; }, [load, flush]);
  useEffect(() => {
    if (!focused || !foreground) {
      if (pending.current) { resumePage.current = requestResetsFeed.current; loadAbort.current?.abort(); }
    } else if (resumePage.current !== null && !loading) {
      const reset = resumePage.current;
      resumePage.current = null;
      void load(reset);
    }
  }, [focused, foreground, loading, load]);
  useLayoutEffect(() => () => controller.dispose(), [controller]);
  useLayoutEffect(() => {
    recovery.current.observe(video ? current!.item_id : null, focused && foreground);
    controller.setGate({ focused: focused && !!video && sourceReady && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== current?.item_id, foreground, manuallyPaused: paused || playbackBlocked });
  }, [controller, focused, foreground, paused, playbackBlocked, current?.item_id, video?.playback.expires_at, !!video, sourceReady]);
  useLayoutEffect(() => { controller.setMuted(preferences.muted); }, [controller, preferences.muted]);
  useEffect(() => {
    const listeners = [first, second].map((p, slot) => p.addListener('playingChange', event => { if (event.isPlaying) controller.enforcePlaybackOwner(slot as 0 | 1); }));
    return () => listeners.forEach(listener => listener.remove());
  }, [controller, first, second]);
  useEffect(() => { const subscription = AppState.addEventListener('change', state => { const active = state === 'active'; if (!active) interaction.reset(); visibility.current.foreground = active; const selected = itemRef.current; const stale = selected && selected.kind !== 'quiz' && needsPlaybackRefresh(selected.video.playback.expires_at); controller.setGate({ foreground: active, ...(active && stale ? { focused: false } : {}) }); setForeground(active); emit(active ? 'app_foregrounded' : 'app_backgrounded', player.currentTime * 1000, watch.current.totalMs); if (active) emit('playback_started', player.currentTime * 1000, watch.current.totalMs); void flush(); }); return () => subscription.remove(); }, [controller, player, emit, flush]);
  useEffect(() => {
    resumeSeek.current.clear(); seekAnchor.current = null; setProgress({ position: 0, duration: 0 });
    watch.current = new VisibleWatchTracker(); stalled.current = new PlaybackStallGuard(); setPaused(false); setAnswer(null); setFeedback(null); setGateReady(false); answerKey.current = Crypto.randomUUID(); submittedAnswer.current = null;
    if (video) emit('playback_started');
  }, [current?.item_id, emit]);
  useLayoutEffect(() => {
    if (video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== current?.item_id) void controller.setSelection(video.playback.url);
  }, [current?.item_id, video?.playback.url, video?.playback.expires_at, controller]);
  useEffect(() => {
    if (video && current && focused && foreground && (needsPlaybackRefresh(video.playback.expires_at) || (playback.error && playback.sourceUri === video.playback.url)) && recovery.current.claim(current.item_id)) void retryVideo();
  }, [current?.item_id, focused, foreground, video?.playback.expires_at, video?.playback.url, playback.error, playback.sourceUri]);
  // React has now attached the selected surface; reapply the existing playback gates.
  useEffect(() => { if (sourceReady) controller.setGate({}); }, [controller, sourceReady, playback.selection]);
  async function resolveVideo(item: UnifiedVideo, signal?: AbortSignal) {
    const route = item.kind === 'study_video' ? 'learning' : 'entertainment';
    return parsePlayback(await api.request(`/v1/${route}/videos/${encodeURIComponent(item.video.video_id)}/playback`, { signal }));
  }
  useUpcomingPlayback<UnifiedItem>(next, next?.video.playback, controller, sourceReady && focused && foreground, transitioning,
    (item, signal) => {
      if (item.kind === 'quiz') throw new Error('Quiz cards have no playback source');
      return resolveVideo(item, signal);
    },
    (item, update) => {
      if (item.kind === 'quiz') return;
      const queue = values.current;
      const updated = updateUpcomingPlayback(queue, indexRef.current, item, update, (clip, playback) =>
        clip.kind === 'quiz' ? clip : { ...clip, video: { ...clip.video, playback } });
      if (updated === queue) return;
      if (update.kind === 'remove') unavailableVideos.current.add(item.video.video_id);
      values.current = updated;
      setItems(updated);
    },
  );
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
  useEffect(() => { if (shouldPrefetchPage({ index, count: items.length, hasNext: !!cursor.current, focused: focused && sourceReady && frameRendered, foreground, loading, hasError: !!error }) && (!presentation.current || items.length - index <= 2) && items.at(-1)?.kind !== 'quiz') void load(); }, [index, items, focused, foreground, loading, error, load, sourceReady, frameRendered]);
  useEffect(() => {
    if (!focused || !foreground || items.length) return;
    const timer = setInterval(() => { if (!pending.current) void load(); }, 10000);
    return () => clearInterval(timer);
  }, [focused, foreground, items.length, load]);
  const quizAnswered = feedback !== null;
  useEffect(() => { if (!focused || !foreground || current?.kind !== 'quiz' || quizAnswered) return; let cancelled = false;
    events.flush().then(() => api.request<{scroll_locked: boolean}>(`/v1/feed/sessions/${session.current}/quiz-gate`, { method: 'POST', headers: { 'Idempotency-Key': current.item_id }, body: { item_id: current.item_id, quiz_instance_id: current.quiz.quiz_instance_id } })).then(result => { if (!cancelled) { setGateReady(result.scroll_locked); if (!result.scroll_locked) void load(true); } }).catch(problem => { if (!cancelled) setError(problem.message); });
    return () => { cancelled = true; };
  }, [current?.item_id, focused, foreground, api, load, events, gateAttempt, quizAnswered]);
  const move = useRef((nextIndex: number) => {});
  move.current = nextIndex => { if (nextIndex === indexRef.current || itemRef.current?.kind === 'quiz') return; interaction.reset(); emit('video_skipped', player.currentTime * 1000, watch.current.totalMs); if (itemRef.current) terminal.current.add(itemRef.current.item_id); void flush(); controller.setGate({ focused: false }); indexRef.current = nextIndex; setIndex(nextIndex); };
  const viewable = useRef(({ viewableItems }: { viewableItems: { item: UnifiedItem }[] }) => {
    const visible = viewableItems[0]?.item;
    const index = visible ? values.current.findIndex(item => item.item_id === visible.item_id) : -1;
    if (index >= 0) move.current(index);
  }).current;
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
    const anchor = seekAnchor.current;
    resumeSeek.current.capture(itemId, anchor?.itemId === itemId ? Math.max(anchor.positionMs, player.currentTime * 1000) : player.currentTime * 1000, playback.selection);
    controller.setGate({ focused: false }); setRenderedSelection(null);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    try {
      const fresh = await resolveVideo(current);
      if (!mounted.current || itemRef.current?.item_id !== itemId) return;
      if (needsPlaybackRefresh(fresh.expires_at)) throw new Error('The refreshed video link has expired. Retry shortly.');
      values.current = values.current.map(item => item.item_id === itemId && item.kind !== 'quiz' ? { ...item, video: { ...item.video, playback: fresh } } : item);
      setItems(values.current);
      await controller.setSelection(fresh.url, undefined, true);
      if (mounted.current && itemRef.current?.item_id === itemId) controller.setGate({ focused: visibility.current.focused && visibility.current.foreground });
    } catch (problem) {
      if (!mounted.current || itemRef.current?.item_id !== itemId) return;
      if (isUnavailablePlayback(problem)) {
        unavailableVideos.current.add(current.video.video_id);
        const at = indexRef.current;
        if (values.current[at + 1]) {
          move.current(at + 1);
          list.current?.scrollToIndex({ index: at + 1, animated: false });
          return;
        }
      }
      controller.reportError();
      setError(isUnavailablePlayback(problem) ? 'This video is unavailable. Swipe or reload to continue.' : 'Could not load this video. Try again.');
    }
    finally { if (retryingVideo.current === itemId) retryingVideo.current = null; }
  }
  const entertainment = current?.kind === 'entertainment_video' ? current.video : null;
  const liked = !!entertainment && clickedIds.includes(entertainment.video_id);
  // FlatList cells can hold an old closure; read the latest state so a second double-tap never un-clicks.
  const doubleTap = useRef(() => {}); doubleTap.current = () => { if (entertainment && !clickedIds.includes(entertainment.video_id)) socialAction(onClickVideo); };
  const saved = !!entertainment && savedIds.includes(entertainment.video_id);
  const showMore = !!video && index === items.length - 1;

  function onFrame(selection: number) {
    if (selectionRef.current !== selection) return;
    const id = itemRef.current?.item_id;
    const target = id ? resumeSeek.current.takeTarget(id, selection, Date.now()) : null;
    if (target !== null) { controller.seekTo(target / 1000); watch.current.sample(target, Date.now(), false); }
    setRenderedSelection(selection); startupTrace.frame();
  }
  function beginScrub() {
    if (!video || !current || current.kind === 'quiz') return;
    emit('playback_progress', player.currentTime * 1000, watch.current.totalMs);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    interaction.scrub(true); controller.setGate({ manuallyPaused: true });
  }
  async function seek(seconds: number) {
    if (!video || !current || current.kind === 'quiz' || !session.current || !Number.isFinite(player.duration) || player.duration <= 0) return;
    const itemId = current.item_id;
    const target = Math.max(0, Math.min(seconds, player.duration - 0.25));
    const isCurrent = () => mounted.current && itemRef.current?.item_id === itemId;
    setSeekBusy(true);
    const applySeek = async () => {
      const anchor = { itemId, positionMs: target * 1000, settling: true };
      seekAnchor.current = anchor;
      controller.seekTo(target);
      const landed = await waitForNativeSeek(target, () => player.currentTime, isCurrent);
      if (!isCurrent()) return;
      anchor.settling = false;
      if (!landed) {
        controller.reportError(true);
        throw new Error('Unable to seek. Try again.');
      }
      const position = player.currentTime;
      watch.current.sample(position * 1000, Date.now(), false);
      setProgress({ position, duration: player.duration });
    };
    try {
      // Previously watched rows can replay locally; they no longer earn credit.
      if (terminal.current.has(itemId)) await applySeek();
      else await seekFeedVideo({ api, events, sessionId: session.current, itemId, eventId: Crypto.randomUUID(), positionMs: target * 1000, visibleWatchMs: watch.current.totalMs,
        isActive: () => isCurrent() && visibility.current.foreground && visibility.current.focused,
        isCurrent,
        onSeek: applySeek,
      });
    } finally { if (mounted.current) setSeekBusy(false); }
  }
  return (
    <View style={styles.screen} onLayout={event => setHeight(event.nativeEvent.layout.height)}>
      <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, !preferences.reducedMotion && { transform: [{ translateY: Animated.add(Animated.multiply(scrollY, -1), index * height) }] }]}><BufferedVideoViews players={[first, second]} playback={playback} sourceReady={sourceReady} visible={!!video} fill={fill} onFrame={onFrame} adjacent={{ height, nextUrl, previousUrl }} /></Animated.View>
      {height > 0 && items.length > 0 ? (
        <Animated.FlatList
          key={listRevision}
          ref={list}
          data={items}
          extraData={[index, answer, feedback, gateReady, busy, loading, error, paused, gesture.hidden, preferences.captions]}
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
                  headerSpace={insets.top + 64}
                  answer={answer}
                  feedback={feedback}
                  busy={busy}
                  continuing={loading}
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
                  {cardIndex === index && <FeedTouchArea interaction={interaction} paused={paused} error={!!playback.error} reducedMotion={preferences.reducedMotion} onToggle={() => setPaused(value => !value)} onDoubleTap={item.kind === 'entertainment_video' ? () => doubleTap.current() : undefined} />}
                  {!gesture.hidden && <FeedCaption
                    courseTitle={item.kind === 'study_video' ? studyCourseLabel(item.course_context) : undefined}
                    byline={item.kind === 'entertainment_video' ? item.video.creator?.display_name || item.video.creator?.handle : undefined}
                    title={item.video.title}
                    caption={preferences.captions ? item.video.caption || (item.kind === 'entertainment_video' ? item.reason_text : undefined) : undefined}
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
              <FeedIconButton reducedMotion={preferences.reducedMotion} count={video?.like_count} label={liked ? 'Unclick video' : 'This clicks'} icon={liked ? 'flash' : 'flash-outline'} selected={liked} color={liked ? theme.colors.coral : theme.colors.text} onPress={() => socialAction(onClickVideo)} />
              <FeedIconButton reducedMotion={preferences.reducedMotion} count={video?.comment_count} label="Comments" icon="chatbubble-outline" onPress={() => interaction.openComments()} />
              <FeedIconButton reducedMotion={preferences.reducedMotion} label={saved ? 'Unsave video' : 'Save video'} icon={saved ? 'bookmark' : 'bookmark-outline'} selected={saved} color={saved ? theme.colors.gold : theme.colors.text} onPress={() => socialAction(onSaveVideo)} />
              {entertainment.source_url && <FeedIconButton reducedMotion={preferences.reducedMotion} label="Share original video" icon="paper-plane-outline" onPress={() => socialAction(clip => { if (clip.source_url) void Share.share({ message: clip.source_url }).catch(() => setError('Unable to open sharing.')); })} />}
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
      {focused && foreground && sourceReady && !paused && !playbackBlocked && (
        <FeedPlaybackWake key={playback.activeSlot} player={player} />
      )}
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
