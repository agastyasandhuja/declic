import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, AppState, FlatList, Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useVideoPlayer, type VideoPlayer } from 'expo-video';
import * as Crypto from 'expo-crypto';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../../state/AuthProvider';
import { ApiError } from '../../lib/api/client';
import { PlaybackRecovery, needsPlaybackRefresh } from '../../lib/playback/PlaybackRecovery';
import { BufferedVideoViews } from '../../lib/playback/BufferedVideoViews';
import { BufferedPlayerController, type BufferedPlaybackState } from '../../lib/playback/BufferedPlayerController';
import type { PlayerDriver } from '../../lib/playback/SinglePlayerController';
import { VisibleWatchTracker, FirstFrameGuard } from '../../lib/playback/VisibleWatchTracker';
import { Ionicons } from '@expo/vector-icons';
import { PlaybackStallGuard } from '../../lib/playback/VisibleWatchTracker';
import { parseFeedPage, parsePlayback } from '../../contracts/validate';
import type { EntertainmentVideo } from '../../contracts/generated';
import { Button } from '../../components/Button';
import { Brand } from '../../components/Brand';
import { theme } from '../../theme';
import type { PlaybackPreferences } from '../settings/ProfileScreen';
import { FeedEventBuffer } from './FeedEventBuffer';
import { createPageReader } from './paging';
import { shouldPrefetchPage } from './source';
import { appendUnified, parseUnifiedPage, type UnifiedItem } from './unified';

export function UnifiedFeedScreen({ focused, preferences, setPreferences, clickedIds, savedIds, onClickVideo, onSaveVideo }: { focused: boolean; preferences: PlaybackPreferences; setPreferences(value: PlaybackPreferences): void; clickedIds: string[]; savedIds: string[]; onClickVideo(video: EntertainmentVideo): void; onSaveVideo(video: EntertainmentVideo): void }) {
  const { api } = useAuth(); const insets = useSafeAreaInsets();
  const [items, setItems] = useState<UnifiedItem[]>([]); const [index, setIndex] = useState(0); const [height, setHeight] = useState(0);
  const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  const [foreground, setForeground] = useState(AppState.currentState === 'active'); const [paused, setPaused] = useState(false);
  const [fill, setFill] = useState(false);
  const [gateAttempt, setGateAttempt] = useState(0);
  const [gateReady, setGateReady] = useState(false); const [answer, setAnswer] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [playback, setPlayback] = useState<BufferedPlaybackState>({ loading: true, ready: false, error: null, activeSlot: 0, timedOut: false, sourceUri: null, selection: 0 });
  const [renderedSelection, setRenderedSelection] = useState<number | null>(null);
  const selectionRef = useRef(playback.selection); selectionRef.current = playback.selection;
  const firstFrame = useRef(new FirstFrameGuard()); const stalled = useRef(new PlaybackStallGuard());
  const loadAbort = useRef<AbortController | null>(null); const resumePage = useRef(false);
  const session = useRef<string | null>(null); const sessionPromise = useRef<Promise<string> | null>(null);
  const cursor = useRef<string | null>(null); const pending = useRef(false); const mounted = useRef(true);
  const generation = useRef(0); const revision = useRef<number | null>(null);
  const recovery = useRef(new PlaybackRecovery());
  const terminal = useRef(new Set<string>()); const retryingVideo = useRef<string | null>(null);
  const itemRef = useRef<UnifiedItem | undefined>(undefined); const indexRef = useRef(0); indexRef.current = index;
  const heightRef = useRef(height); heightRef.current = height;
  const list = useRef<FlatList<UnifiedItem>>(null); const values = useRef(items); values.current = items;
  const events = useMemo(() => new FeedEventBuffer(api), [api]);
  const watch = useRef(new VisibleWatchTracker()); const answerKey = useRef(Crypto.randomUUID()); const submittedAnswer = useRef<string | null>(null);
  const setup = (p: VideoPlayer) => { p.loop = true; p.staysActiveInBackground = false; p.audioMixingMode = 'doNotMix'; p.bufferOptions = { preferredForwardBufferDuration: 5 }; };
  const first = useVideoPlayer(null, setup); const second = useVideoPlayer(null, setup);
  const controller = useMemo(() => new BufferedPlayerController([first, second].map(p => ({ play: () => p.play(), pause: () => p.pause(), replaceAsync: (uri: string | null) => p.replaceAsync(uri ? { uri } : null) })) as [PlayerDriver, PlayerDriver], setPlayback), [first, second]);
  const player = playback.activeSlot === 0 ? first : second;
  const visibility = useRef({ focused, foreground }); visibility.current = { focused, foreground };
  const current = items[index]; itemRef.current = current;
  const video = current && current.kind !== 'quiz' ? current.video : null;
  const sourceReady = !!video && playback.ready && playback.sourceUri === video.playback.url;
  const frameRendered = renderedSelection === playback.selection;
  const next = items[index + 1]; const nextUrl = next && next.kind !== 'quiz' ? next.video.playback.url : undefined;
  const emit = useCallback((type: string, position = 0, watched = 0, item = itemRef.current) => {
    if (!session.current || !item || item.kind === 'quiz' || terminal.current.has(item.item_id)) return;
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
      const query = new URLSearchParams({ session_id: id, limit: '5' });
      if (!reset && cursor.current) query.set('cursor', cursor.current);
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
    controller.setGate({ focused: focused && !!video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== current?.item_id, foreground, manuallyPaused: paused });
  }, [controller, focused, foreground, paused, current?.item_id, video?.playback.expires_at, !!video]);
  useEffect(() => { first.muted = preferences.muted; second.muted = preferences.muted; }, [first, second, preferences.muted]);
  useEffect(() => { const subscription = AppState.addEventListener('change', state => { const active = state === 'active'; visibility.current.foreground = active; const selected = itemRef.current; const stale = selected && selected.kind !== 'quiz' && needsPlaybackRefresh(selected.video.playback.expires_at); controller.setGate({ foreground: active, ...(active && stale ? { focused: false } : {}) }); setForeground(active); emit(active ? 'app_foregrounded' : 'app_backgrounded', player.currentTime * 1000, watch.current.totalMs); if (active) emit('playback_started', player.currentTime * 1000, watch.current.totalMs); void flush(); }); return () => subscription.remove(); }, [controller, player, emit, flush]);
  useEffect(() => {
    watch.current = new VisibleWatchTracker(); stalled.current = new PlaybackStallGuard(); setPaused(false); setAnswer(null); setExplanation(null); setGateReady(false); answerKey.current = Crypto.randomUUID(); submittedAnswer.current = null;
    if (video) emit('playback_started');
  }, [current?.item_id, emit]);
  useEffect(() => {
    if (video && !needsPlaybackRefresh(video.playback.expires_at) && retryingVideo.current !== current?.item_id) void controller.setSelection(video.playback.url, nextUrl);
  }, [current?.item_id, video?.playback.url, controller]);
  useEffect(() => {
    if (video && current && focused && foreground && (needsPlaybackRefresh(video.playback.expires_at) || (playback.error && playback.sourceUri === video.playback.url)) && recovery.current.claim(current.item_id)) void retryVideo();
  }, [current?.item_id, focused, foreground, video?.playback.expires_at, video?.playback.url, playback.error, playback.sourceUri]);
  // React has now attached the selected surface; reapply the existing playback gates.
  useEffect(() => { if (sourceReady) controller.setGate({}); }, [controller, sourceReady, playback.selection]);
  useEffect(() => { if (playback.ready) controller.preload(nextUrl); }, [controller, playback.ready, nextUrl]);
  useEffect(() => {
    if (!video) return;
    let ticks = 0;
    const enabled = focused && foreground && !paused && sourceReady;
    firstFrame.current.sample(playback.selection, frameRendered, Date.now(), enabled);
    stalled.current.sample(player.currentTime * 1000, Date.now(), enabled);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    const timer = setInterval(() => {
      const position = player.currentTime * 1000;
      if (stalled.current.sample(position, Date.now(), enabled) || firstFrame.current.sample(playback.selection, frameRendered, Date.now(), enabled)) controller.reportError(true);
      if (sourceReady && player.status === 'error') controller.reportError();
      const total = watch.current.sample(position, Date.now(), enabled && frameRendered && player.playing && player.status === 'readyToPlay', player.duration * 1000);
      if (++ticks % 6 === 0) { emit('playback_progress', position, total); void flush(); }
    }, 500);
    return () => clearInterval(timer);
  }, [current?.item_id, player, focused, foreground, paused, sourceReady, playback.selection, frameRendered, emit, flush]);
  useEffect(() => { if (shouldPrefetchPage({ index, count: items.length, hasNext: !!cursor.current, focused, foreground, loading, hasError: !!error }) && items.at(-1)?.kind !== 'quiz') void load(); }, [index, items, focused, foreground, loading, error, load]);
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
  move.current = nextIndex => { if (nextIndex === indexRef.current || itemRef.current?.kind === 'quiz') return; emit('video_skipped', player.currentTime * 1000, watch.current.totalMs); if (itemRef.current) terminal.current.add(itemRef.current.item_id); void flush(); controller.setGate({ focused: false }); indexRef.current = nextIndex; setIndex(nextIndex); };
  const viewable = useRef(({ viewableItems }: { viewableItems: { index?: number | null }[] }) => { const i = viewableItems[0]?.index; if (i != null) move.current(i); }).current;
  async function submit() {
    if (current?.kind !== 'quiz' || !answer || !gateReady || busy) return;
    setBusy(true); setError(null); submittedAnswer.current ??= answer;
    try { const result = await api.request<{ explanation: string; scroll_unlocked: boolean }>(`/v1/quizzes/${current.quiz.quiz_instance_id}/answers`, { method: 'POST', headers: { 'Idempotency-Key': answerKey.current }, body: { session_id: session.current, selected_option_id: submittedAnswer.current } }); if (!result.scroll_unlocked) throw new Error('Please retry your answer.'); setExplanation(result.explanation); cursor.current = null; }
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
    controller.setGate({ focused: false }); setRenderedSelection(null);
    watch.current.sample(player.currentTime * 1000, Date.now(), false);
    try {
      const route = current.kind === 'study_video' ? 'learning' : 'entertainment';
      const fresh = parsePlayback(await api.request(`/v1/${route}/videos/${video.video_id}/playback`));
      if (!mounted.current || itemRef.current?.item_id !== itemId) return;
      if (needsPlaybackRefresh(fresh.expires_at)) throw new Error('The refreshed video link has expired. Retry shortly.');
      setItems(old => old.map(item => item.item_id === itemId && item.kind !== 'quiz' ? { ...item, video: { ...item.video, playback: fresh } } : item));
      await controller.setSelection(fresh.url, nextUrl, true);
      if (mounted.current && itemRef.current?.item_id === itemId) controller.setGate({ focused: visibility.current.focused && visibility.current.foreground });
    } catch (problem) { if (mounted.current && itemRef.current?.item_id === itemId) { controller.reportError(); setError(problem instanceof Error ? problem.message : 'This video is unavailable.'); } }
    finally { if (retryingVideo.current === itemId) retryingVideo.current = null; }
  }
  return <View style={styles.screen} onLayout={event => setHeight(event.nativeEvent.layout.height)}>
    <BufferedVideoViews players={[first, second]} playback={playback} sourceReady={sourceReady} visible={!!video} fill={fill} onFrame={selection => { if (selectionRef.current === selection) setRenderedSelection(selection); }} />
    {height > 0 && items.length > 0 ? <FlatList ref={list} data={items} extraData={[index, answer, explanation, gateReady, busy]} removeClippedSubviews={false} initialNumToRender={2} maxToRenderPerBatch={2} windowSize={3} keyExtractor={item => item.item_id} pagingEnabled scrollEnabled={current?.kind !== 'quiz'} showsVerticalScrollIndicator={false} getItemLayout={(_, i) => ({ length: height, offset: i * height, index: i })} viewabilityConfig={{ itemVisiblePercentThreshold: 80 }} onViewableItemsChanged={viewable} renderItem={({ item }) => <View style={{ height }}>
      {item.kind === 'quiz' ? <ScrollView contentContainerStyle={styles.quizContent}><Text style={styles.eyebrow}>QUICK CHECK</Text><Text style={styles.title}>{item.quiz.prompt}</Text>{item.quiz.options.map(option => <Pressable accessibilityRole="radio" accessibilityState={{ checked: answer === option.option_id }} key={option.option_id} disabled={!!explanation || busy || submittedAnswer.current !== null} onPress={() => setAnswer(option.option_id)} style={[styles.option, answer === option.option_id && { borderColor: theme.colors.accent }]}><Text style={styles.text}>{option.text}</Text></Pressable>)}{explanation ? <><Text style={styles.text}>{explanation}</Text><Button title="Keep scrolling" onPress={() => void load(true)} /></> : <><Text style={styles.muted}>Answer to continue. Getting it wrong is part of learning.</Text><Button title={gateReady ? 'Check answer' : 'Preparing question…'} busy={busy} disabled={!gateReady || !answer} onPress={() => void submit()} /></>}</ScrollView> : <><Pressable style={StyleSheet.absoluteFill} accessibilityLabel={paused ? 'Play video' : 'Pause video'} onPress={() => setPaused(p => !p)} /><View style={styles.caption}><Text style={styles.eyebrow}>{item.kind === 'study_video' ? item.course_context?.title ?? 'YOUR COURSES' : 'FOR YOU'}</Text><Text style={styles.title}>{item.video.title ?? item.video.creator?.handle ?? 'Discover'}</Text>{preferences.captions && <Text numberOfLines={3} style={styles.text}>{item.video.caption ?? item.reason_text}</Text>}{item.item_id === items.at(-1)?.item_id && <Button title={loading ? 'Loading…' : 'More videos'} secondary onPress={() => void load(!cursor.current)} />}</View></>}
    </View>} /> : <View style={styles.quiz}><Text style={styles.title}>Your next déclic is on its way.</Text><Text style={styles.text}>Connect Instagram and Canvas in Courses. Your feed fills as clips and lessons become ready.</Text>{loading ? <ActivityIndicator color={theme.colors.accent} /> : <Button title="Refresh feed" onPress={() => void load(true)} />}</View>}
    {video && <View style={styles.actions}>{current?.kind === 'entertainment_video' && <><Pressable accessibilityRole="button" accessibilityLabel="This clicks" onPress={() => socialAction(onClickVideo)}><Ionicons name={clickedIds.includes(video.video_id) ? 'heart' : 'heart-outline'} size={30} color={theme.colors.coral} /></Pressable><Pressable accessibilityRole="button" accessibilityLabel="Save video" onPress={() => socialAction(onSaveVideo)}><Ionicons name={savedIds.includes(video.video_id) ? 'bookmark' : 'bookmark-outline'} size={28} color={theme.colors.accent} /></Pressable><Pressable accessibilityRole="button" accessibilityLabel="Open original post" onPress={() => socialAction(clip => { if (clip.source_url) void Linking.openURL(clip.source_url).catch(() => setError('Unable to open this post.')); })}><Ionicons name="open-outline" size={24} color={theme.colors.text} /></Pressable></>}<Pressable accessibilityRole="button" accessibilityLabel={fill ? 'Fit video' : 'Fill screen'} onPress={() => setFill(v => !v)}><Ionicons name="resize-outline" size={26} color={theme.colors.text} /></Pressable>{index + 1 < items.length && <Pressable accessibilityRole="button" accessibilityLabel="Next video" onPress={() => { move.current(index + 1); list.current?.scrollToIndex({ index: index + 1, animated: !preferences.reducedMotion }); }}><Ionicons name="chevron-down" size={28} color={theme.colors.text} /></Pressable>}</View>}
    <View pointerEvents="box-none" style={[styles.header, { top: insets.top + 12 }]}><Brand size={25} /><Pressable accessibilityRole="button" onPress={() => setPreferences({ ...preferences, muted: !preferences.muted })}><Text style={styles.text}>{preferences.muted ? 'Unmute' : 'Mute'}</Text></Pressable></View>
    {video && (!sourceReady || !frameRendered || playback.error) && <View style={styles.playback}>{playback.error ? <Button title="Retry video" onPress={() => void retryVideo()} /> : <ActivityIndicator color={theme.colors.accent} />}</View>}
    {error && <View style={styles.error}><Text accessibilityRole="alert" style={styles.text}>{error}</Text>{current?.kind === 'quiz' && gateReady && <Button title="Continue without grading" secondary onPress={() => void recoverQuiz()} />}<Button title="Retry" secondary onPress={() => { if (current?.kind === 'quiz') { if (answer && gateReady) void submit(); else { setError(null); setGateAttempt(n => n + 1); } } else void load(!cursor.current); }} /></View>}
  </View>;
}
const styles = StyleSheet.create({ actions: { position: 'absolute', right: 20, bottom: 200, gap: 24, padding: 12, borderRadius: 24, backgroundColor: '#08070DAA' }, screen: { flex: 1, backgroundColor: '#08070D' }, header: { position: 'absolute', left: 24, right: 24, flexDirection: 'row', justifyContent: 'space-between' }, caption: { position: 'absolute', bottom: 30, left: 22, right: 22, gap: 8, padding: 14, borderRadius: 18, backgroundColor: '#08070DBB' }, quizContent: { flexGrow: 1, justifyContent: 'center', padding: 26, paddingTop: 90, paddingBottom: 32, gap: 18 }, quiz: { flex: 1, justifyContent: 'center', padding: 26, gap: 18 }, title: { color: theme.colors.text, fontSize: 23, fontWeight: '700' }, text: { color: theme.colors.text, fontSize: 16, lineHeight: 23 }, muted: { color: theme.colors.muted, fontSize: 14 }, eyebrow: { color: theme.colors.accent, fontSize: 12, fontWeight: '700' }, option: { backgroundColor: theme.colors.surface, borderWidth: 2, borderColor: theme.colors.elevated, borderRadius: 16, padding: 16 }, playback: { position: 'absolute', top: '45%', alignSelf: 'center' }, error: { position: 'absolute', top: 100, left: 20, right: 20, padding: 16, gap: 8, backgroundColor: theme.colors.surface, borderRadius: 16 } });
