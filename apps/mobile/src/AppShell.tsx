import { MediaCacheBoundary } from './lib/playback/MediaCache';
import { UnifiedFeedScreen } from './features/feed/UnifiedFeedScreen';
import React, { useCallback, useMemo, useState, useEffect, useRef } from 'react';
import { AccessibilityInfo, ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider, useAuth } from './state/AuthProvider';
import { useFonts } from 'expo-font';
import { ProfileScreen, type PlaybackPreferences } from './features/settings/ProfileScreen';
import type { EntertainmentVideo } from './contracts/generated';
import { AuthScreen } from './features/auth/AuthScreen';
import { FeedScreen, type LocalPlaybackEvent } from './features/feed/FeedScreen';
import { FeedHistory, createApiFeedSource, createFixtureSource, createSavedInstagramSource } from './features/feed/source';
import savedInstagramCatalog from '@local/instagram-preview';
import { parseFeedPage } from './contracts/validate';
import { CoursesScreen } from './features/settings/CoursesScreen';
import { LabScreen } from './features/settings/LabScreen';
import { featureRegistry } from './integration/registry';
import { config } from './config';
import { theme, sharedStyles as s } from './theme';
import { Button } from './components/Button';

type Route = 'feed' | 'courses' | 'profile' | 'lab';
const savedInstagramPage = parseFeedPage(savedInstagramCatalog);
const savedInstagramSource = __DEV__ && Platform.OS === 'ios' && savedInstagramPage.items.length ? createSavedInstagramSource(savedInstagramPage) : null;
function SignedInShell() {
  const { user, api, mode } = useAuth(); const insets = useSafeAreaInsets();
  const history = useRef(new FeedHistory()).current;
  const [clicked, setClicked] = useState<EntertainmentVideo[]>([]);
  const [saved, setSaved] = useState<EntertainmentVideo[]>([]);
  const [replay, setReplay] = useState<EntertainmentVideo | null>(null);
  const [preferences, setPreferences] = useState<PlaybackPreferences>({ muted: Platform.OS === 'web', captions: true, reducedMotion: false });
  useEffect(() => { void AccessibilityInfo.isReduceMotionEnabled().then(reducedMotion => setPreferences(p => ({ ...p, reducedMotion }))).catch(() => undefined); const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', reducedMotion => setPreferences(p => ({ ...p, reducedMotion }))); return () => subscription.remove(); }, []);
  const toggle = (setter: React.Dispatch<React.SetStateAction<EntertainmentVideo[]>>, video: EntertainmentVideo) => setter(items => items.some(item => item.video_id === video.video_id) ? items.filter(item => item.video_id !== video.video_id) : [...items.slice(-99), video]);
  const [immersive, setImmersive] = useState(false);
  const [route, setRoute] = useState<Route>('feed'); const [feature, setFeature] = useState<'academics' | 'learning' | null>(null);
  const [brokenClip, setBrokenClip] = useState(false); const [live, setLive] = useState(mode === 'signed_in' && config.feedSource === 'api');
  const [savedInstagram, setSavedInstagram] = useState(Boolean(savedInstagramSource));
  const [feedRevision, setFeedRevision] = useState(0);
  const savedInstagramAvailable = Boolean(savedInstagramSource);
  const [events, setEvents] = useState<LocalPlaybackEvent[]>([]);
  const onEvent = useCallback((event: LocalPlaybackEvent) => setEvents(previous => [...previous.slice(-19), event]), []);
  const baseSource = useMemo(() => live ? createApiFeedSource(api) : savedInstagram && savedInstagramSource ? savedInstagramSource : createFixtureSource(), [live, api, savedInstagram]);
  const source = useMemo(() => replay ? { ...baseSource, getPage: async () => { const playback = replay.playback.expires_at && Date.parse(replay.playback.expires_at) <= Date.now() ? await baseSource.resolvePlayback(replay.video_id) : replay.playback; return { schema_version: '1' as const, items: [{ ...replay, playback }], next_cursor: null }; } } : baseSource, [baseSource, replay]);
  const Feature = feature ? featureRegistry[feature] : null;
  return <View style={s.screen}>
    <View style={[styles.screen, route !== 'feed' || feature ? styles.hidden : undefined]}>{live && !replay ? <UnifiedFeedScreen key={feedRevision} onImmersiveChange={setImmersive} clickedIds={clicked.map(v => v.video_id)} savedIds={saved.map(v => v.video_id)} onClickVideo={video => toggle(setClicked, video)} onSaveVideo={video => toggle(setSaved, video)} focused={route === 'feed' && !feature} preferences={preferences} setPreferences={setPreferences} /> : <FeedScreen onImmersiveChange={setImmersive} key={`${source.mode}:${replay?.video_id ?? ''}:${brokenClip}:${feedRevision}`} source={source} history={history} allowReplay={Boolean(replay)} focused={route === 'feed' && !feature} brokenClip={brokenClip && source.mode === 'fixture'} onEvent={onEvent} onReload={() => { setReplay(null); setFeedRevision(value => value + 1); }} preferences={preferences} setPreferences={setPreferences} clickedIds={clicked.map(v => v.video_id)} savedIds={saved.map(v => v.video_id)} onClickVideo={video => toggle(setClicked, video)} onSaveVideo={video => toggle(setSaved, video)} />}</View>
    {feature && user ? <View style={styles.screen}>{Feature ? <Feature user={user} api={api} theme={theme} isPreview={mode === 'preview'} onBack={() => setFeature(null)} onOpenFeed={() => { setFeature(null); setRoute('feed'); }} /> : <View style={[styles.placeholder, { paddingTop: insets.top + 30 }]}><Ionicons name={feature === 'academics' ? 'school-outline' : 'sparkles-outline'} size={48} color={theme.colors.accent} /><Text style={s.eyebrow}>INTEGRATION WORKSPACE</Text><Text style={s.title}>{feature === 'academics' ? 'Course connection,\ncoming together.' : 'A new way to\nunderstand.'}</Text><Text style={s.subtitle}>This slot is ready for {feature === 'academics' ? 'Amogh’s academic' : 'Agastya’s learning'} components. Shared identity, API client, and theme are available through explicit props.</Text><Button title="Back to the lab" secondary onPress={() => setFeature(null)} /></View>}</View> : route === 'courses' ? <View style={styles.screen}><CoursesScreen onFeedSettingsChanged={() => setFeedRevision(value => value + 1)} /></View> : route === 'profile' ? <View style={styles.screen}><ProfileScreen clicked={clicked} saved={saved} onOpen={video => { setReplay(video); setRoute('feed'); }} preferences={preferences} setPreferences={setPreferences} openCourses={() => setRoute('courses')} openLab={() => setRoute('lab')} /></View> : route === 'lab' && __DEV__ ? <View style={styles.screen}><LabScreen brokenClip={brokenClip} setBrokenClip={setBrokenClip} savedInstagram={savedInstagram} savedInstagramAvailable={savedInstagramAvailable} setSavedInstagram={value => { setSavedInstagram(value); if (value) setLive(false); }} live={live} setLive={value => { setLive(value); if (value) setSavedInstagram(false); }} events={events} openFeature={setFeature} /></View> : null}
    <View pointerEvents={immersive ? "none" : "auto"} accessibilityElementsHidden={immersive} importantForAccessibility={immersive ? "no-hide-descendants" : "auto"} style={[styles.tabs, { opacity: immersive ? 0 : 1, paddingBottom: Math.max(insets.bottom, 12) }]}><View style={styles.tabTrack}>{([{ key: 'feed', label: 'Feed', icon: 'play-circle', inactive: 'play-circle-outline' }, { key: 'courses', label: 'Courses', icon: 'school', inactive: 'school-outline' }, { key: 'profile', label: 'You', icon: 'person-circle', inactive: 'person-circle-outline' }] as const).map(tab => <Pressable key={tab.key} accessibilityRole="tab" accessibilityLabel={tab.label} accessibilityState={{ selected: route === tab.key && !feature }} testID={`tab-${tab.key}`} onPress={() => { setFeature(null); setRoute(tab.key); if (tab.key === 'feed') setReplay(null); }} style={[styles.tab, route === tab.key && !feature && styles.activeIcon]}><Ionicons name={route === tab.key && !feature ? tab.icon : tab.inactive} size={20} color={route === tab.key && !feature ? theme.colors.ink : theme.colors.muted} /><Text style={[styles.tabLabel, route === tab.key && !feature && { color: theme.colors.ink }]}>{tab.label}</Text></Pressable>)}</View></View>
  </View>;
}
function SessionGate() {
  const { mode, user } = useAuth();
  if (mode === 'loading') return <View style={[s.screen, { alignItems: 'center', justifyContent: 'center', gap: 20 }]}><ActivityIndicator color={theme.colors.accent} /><Text style={s.subtitle}>Picking up where you left off…</Text></View>;
  return <MediaCacheBoundary owner={mode === 'signed_in' ? `${config.apiBaseUrl}:${user?.user_id}` : mode === 'preview' ? 'preview' : null}>{mode === 'signed_out' ? <AuthScreen /> : <SignedInShell key={`${mode}:${user?.user_id}`} />}</MediaCacheBoundary>;
}
export default function AppShell() { const [loaded, error] = useFonts({ [theme.fonts.display]: require('../assets/fonts/Syne-ExtraBold.ttf'), [theme.fonts.body]: require('../assets/fonts/PlusJakartaSans-Regular.ttf'), [theme.fonts.bold]: require('../assets/fonts/PlusJakartaSans-Bold.ttf') }); return <SafeAreaProvider><AuthProvider><StatusBar style="light" />{!loaded && !error ? <View style={s.screen}><ActivityIndicator color={theme.colors.accent} /></View> : <SessionGate />}</AuthProvider></SafeAreaProvider>; }
const styles = StyleSheet.create({
  screen: { flex: 1 }, hidden: { display: 'none' }, tabs: { backgroundColor: theme.colors.background, paddingTop: 6, paddingHorizontal: 16 }, tabTrack: { flexDirection: 'row', backgroundColor: theme.colors.surface, padding: 4, borderRadius: 999, borderWidth: 1, borderColor: theme.colors.elevated }, tab: { flex: 1, minHeight: 44, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 6, borderRadius: 999 }, activeIcon: { backgroundColor: theme.colors.text }, tabLabel: { color: theme.colors.muted, fontSize: 13, fontFamily: theme.fonts.bold }, placeholder: { padding: 26, gap: 22, flex: 1 },
});
