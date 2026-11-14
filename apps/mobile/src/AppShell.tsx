import React, { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider, useAuth } from './state/AuthProvider';
import { AuthScreen } from './features/auth/AuthScreen';
import { FeedScreen, type LocalPlaybackEvent } from './features/feed/FeedScreen';
import { createApiFeedSource, createFixtureSource, createSavedInstagramSource } from './features/feed/source';
import savedInstagramCatalog from '@local/instagram-preview';
import { parseFeedPage } from './contracts/validate';
import { CoursesScreen } from './features/settings/CoursesScreen';
import { LabScreen } from './features/settings/LabScreen';
import { featureRegistry } from './integration/registry';
import { config } from './config';
import { theme, sharedStyles as s } from './theme';
import { Button } from './components/Button';

type Route = 'feed' | 'courses' | 'lab';
const savedInstagramPage = parseFeedPage(savedInstagramCatalog);
const savedInstagramSource = __DEV__ && Platform.OS === 'ios' && savedInstagramPage.items.length ? createSavedInstagramSource(savedInstagramPage) : null;
function SignedInShell() {
  const { user, api, mode } = useAuth(); const insets = useSafeAreaInsets();
  const [route, setRoute] = useState<Route>('feed'); const [feature, setFeature] = useState<'academics' | 'learning' | null>(null);
  const [brokenClip, setBrokenClip] = useState(false); const [live, setLive] = useState(mode === 'signed_in' && config.feedSource === 'api');
  const [savedInstagram, setSavedInstagram] = useState(Boolean(savedInstagramSource));
  const [feedRevision, setFeedRevision] = useState(0);
  const savedInstagramAvailable = Boolean(savedInstagramSource);
  const [events, setEvents] = useState<LocalPlaybackEvent[]>([]);
  const onEvent = useCallback((event: LocalPlaybackEvent) => setEvents(previous => [...previous.slice(-19), event]), []);
  const source = useMemo(() => live ? createApiFeedSource(api) : savedInstagram && savedInstagramSource ? savedInstagramSource : createFixtureSource(), [live, api, savedInstagram]);
  const Feature = feature ? featureRegistry[feature] : null;
  return <View style={s.screen}>
    <View style={[styles.screen, route !== 'feed' || feature ? styles.hidden : undefined]}><FeedScreen key={`${source.mode}:${brokenClip}:${feedRevision}`} source={source} focused={route === 'feed' && !feature} brokenClip={brokenClip && source.mode === 'fixture'} onEvent={onEvent} onReload={() => setFeedRevision(value => value + 1)} /></View>
    {feature && user ? <View style={styles.screen}>{Feature ? <Feature user={user} api={api} theme={theme} isPreview={mode === 'preview'} onBack={() => setFeature(null)} onOpenFeed={() => { setFeature(null); setRoute('feed'); }} /> : <View style={[styles.placeholder, { paddingTop: insets.top + 30 }]}><Ionicons name={feature === 'academics' ? 'school-outline' : 'sparkles-outline'} size={48} color={theme.colors.accent} /><Text style={s.eyebrow}>INTEGRATION WORKSPACE</Text><Text style={s.title}>{feature === 'academics' ? 'Course connection,\ncoming together.' : 'A new way to\nunderstand.'}</Text><Text style={s.subtitle}>This slot is ready for {feature === 'academics' ? 'Amogh’s academic' : 'Agastya’s learning'} components. Shared identity, API client, and theme are available through explicit props.</Text><Button title="Back to the lab" secondary onPress={() => setFeature(null)} /></View>}</View> : route === 'courses' ? <View style={styles.screen}><CoursesScreen /></View> : route === 'lab' ? <View style={styles.screen}><LabScreen brokenClip={brokenClip} setBrokenClip={setBrokenClip} savedInstagram={savedInstagram} savedInstagramAvailable={savedInstagramAvailable} setSavedInstagram={value => { setSavedInstagram(value); if (value) setLive(false); }} live={live} setLive={value => { setLive(value); if (value) setSavedInstagram(false); }} events={events} openFeature={setFeature} /></View> : null}
    <View style={[styles.tabs, { paddingBottom: Math.max(insets.bottom, 12) }]}>{([{ key: 'feed', label: 'Your feed', icon: 'play-outline' }, { key: 'courses', label: 'Courses', icon: 'albums-outline' }, { key: 'lab', label: 'The lab', icon: 'options-outline' }] as const).map(tab => <Pressable key={tab.key} accessibilityRole="tab" accessibilityLabel={tab.label} accessibilityState={{ selected: route === tab.key && !feature }} testID={`tab-${tab.key}`} onPress={() => { setFeature(null); setRoute(tab.key); }} style={styles.tab}><View style={[styles.tabIcon, route === tab.key && !feature && styles.activeIcon]}><Ionicons name={tab.icon} size={21} color={route === tab.key && !feature ? theme.colors.accent : '#809079'} /></View><Text style={[styles.tabLabel, route === tab.key && !feature && { color: theme.colors.accent }]}>{tab.label}</Text></Pressable>)}</View>
  </View>;
}
function SessionGate() {
  const { mode, user } = useAuth();
  if (mode === 'loading') return <View style={[s.screen, { alignItems: 'center', justifyContent: 'center', gap: 20 }]}><ActivityIndicator color={theme.colors.accent} /><Text style={s.subtitle}>Picking up where you left off…</Text></View>;
  return mode === 'signed_out' ? <AuthScreen /> : <SignedInShell key={`${mode}:${user?.user_id}`} />;
}
export default function AppShell() { return <SafeAreaProvider><AuthProvider><StatusBar style="light" /><SessionGate /></AuthProvider></SafeAreaProvider>; }
const styles = StyleSheet.create({
  screen: { flex: 1 }, hidden: { display: 'none' }, tabs: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#2A3327', backgroundColor: '#111710', paddingTop: 10 }, tab: { flex: 1, alignItems: 'center', gap: 4 }, tabIcon: { paddingVertical: 5, paddingHorizontal: 23, borderRadius: 17 }, activeIcon: { backgroundColor: '#D5F98512' }, tabLabel: { color: '#809079', fontSize: 10, fontWeight: '600' }, placeholder: { padding: 26, gap: 22, flex: 1 },
});
