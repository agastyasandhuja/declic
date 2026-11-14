import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../components/Button';
import { config } from '../../config';
import { useAuth } from '../../state/AuthProvider';
import { sharedStyles as s, theme } from '../../theme';
import type { LocalPlaybackEvent } from '../feed/FeedScreen';

export function LabScreen({ brokenClip, setBrokenClip, live, setLive, events, openFeature }: { brokenClip: boolean; setBrokenClip(value: boolean): void; live: boolean; setLive(value: boolean): void; events: LocalPlaybackEvent[]; openFeature(key: 'academics' | 'learning'): void }) {
  const { mode, user, signOut, api } = useAuth(); const [message, setMessage] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  async function checkApi() { setBusy(true); try { await api.request('/v1/me'); setMessage('The authenticated /v1/me request succeeded.'); } catch (error) { setMessage(error instanceof Error ? error.message : 'Request failed.'); } finally { setBusy(false); } }
  async function logout() { try { await signOut(); } catch (error) { setMessage(error instanceof Error ? error.message : 'Sign-out failed. Retry.'); } }
  return <SafeAreaView style={s.screen} edges={['top']}><ScrollView contentContainerStyle={styles.content}>
    <Text style={s.eyebrow}>ROOM TO EXPERIMENT</Text><Text style={s.title}>Make it yours.</Text><Text style={s.subtitle}>A small workbench for the team. Try integrations, check playback, and keep building.</Text>
    <View style={s.card}><View style={styles.row}><View style={styles.avatar}><Ionicons name="person-outline" color={theme.colors.accent} size={22} /></View><View style={{ flex: 1 }}><Text style={styles.heading}>{user?.display_name ?? 'Your account'}</Text><Text style={styles.detail}>{mode === 'preview' ? 'Demo session · no API credentials' : 'Supabase session · securely saved on device'}</Text></View></View><Text style={styles.small}>{mode === 'preview' ? 'Synthetic learner' : user?.email}</Text><Button title={mode === 'preview' ? 'Leave demo' : 'Sign out'} secondary onPress={() => void logout()} /></View>
    <Text style={styles.section}>Feature workspaces</Text>
    {[{ key: 'academics' as const, icon: 'school-outline' as const, title: 'Canvas & curriculum', owner: 'Amogh’s integration slot' }, { key: 'learning' as const, icon: 'sparkles-outline' as const, title: 'Learning & quizzes', owner: 'Agastya’s integration slot' }].map(item => <Pressable accessibilityRole="button" key={item.key} onPress={() => openFeature(item.key)} style={styles.feature}><Ionicons name={item.icon} size={23} color={theme.colors.accent} /><View style={{ flex: 1, gap: 5 }}><Text style={styles.heading}>{item.title}</Text><Text style={styles.detail}>{item.owner}</Text></View><Ionicons name="arrow-forward" color={theme.colors.muted} size={18} /></Pressable>)}
    <Text style={styles.section}>Playback & connections</Text>
    <View style={s.card}><View style={styles.row}><View style={{ flex: 1, gap: 7 }}><Text style={styles.heading}>Unavailable clip test</Text><Text style={styles.detail}>Break the first demo clip to try retry and skip. Turn off to restore it.</Text></View><Switch accessibilityLabel="Unavailable clip test" value={brokenClip} onValueChange={setBrokenClip} trackColor={{ true: '#91AD55', false: '#454F40' }} /></View></View>
    <View style={s.card}><View style={styles.row}><View style={{ flex: 1, gap: 7 }}><Text style={styles.heading}>Use connected feed</Text><Text style={styles.detail}>{config.apiBaseUrl ? 'GET /v1/entertainment/feed' : 'Add EXPO_PUBLIC_API_BASE_URL to enable.'}</Text></View><Switch accessibilityLabel="Use connected feed" value={live} onValueChange={setLive} disabled={!config.apiBaseUrl || mode === 'preview'} trackColor={{ true: '#91AD55', false: '#454F40' }} /></View><View style={{ height: 18 }} /><Button title="Check authenticated API" secondary onPress={() => void checkApi()} busy={busy} /></View>
    {message && <Text accessibilityRole="alert" style={styles.message}>{message}</Text>}
    <View style={s.card}><Text style={styles.heading}>Playback activity</Text><Text style={styles.detail}>Local observations only. Nothing is sent to a server yet.</Text>{events.length ? events.slice(-4).reverse().map((event, i) => <Text key={i} style={styles.event}>{event.video_id} · {event.event_type === 'playback_progress' ? `${Math.round(event.visible_watch_ms / 1000)}s visible` : event.event_type.replace('playback_', '').replace('video_', '')}</Text>) : <Text style={styles.small}>Play a clip to see activity here.</Text>}</View>
    <Text style={styles.footer}>PROTOTYPE 0.1 · ATLAS PERSISTENCE DEFERRED</Text>
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({
  content: { padding: 24, paddingTop: 24, gap: 18, maxWidth: 640, width: '100%', alignSelf: 'center', paddingBottom: 36 }, row: { flexDirection: 'row', gap: 15, alignItems: 'center' }, avatar: { width: 46, height: 46, borderRadius: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: '#D5F98512' },
  heading: { color: theme.colors.text, fontSize: 15, fontWeight: '600' }, detail: { color: theme.colors.muted, fontSize: 12, lineHeight: 19 }, small: { color: '#A5B09C', fontSize: 12, marginVertical: 18 }, section: { color: theme.colors.text, fontSize: 18, fontWeight: '600', marginTop: 8 },
  feature: { flexDirection: 'row', alignItems: 'center', gap: 17, backgroundColor: theme.colors.surface, padding: 21, borderRadius: 21, borderWidth: 1, borderColor: theme.colors.border }, message: { color: theme.colors.accent, fontSize: 13, lineHeight: 20 }, event: { color: '#C5D0BE', fontSize: 10, marginTop: 13 }, footer: { color: '#74816D', fontSize: 9, letterSpacing: 1.4, marginTop: 12 },
});
