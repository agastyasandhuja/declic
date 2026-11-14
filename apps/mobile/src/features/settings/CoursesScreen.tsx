import { InstagramConnection } from './InstagramConnection';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, AppState, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import { Button } from '../../components/Button';
import { useAuth } from '../../state/AuthProvider';
import { ApiError } from '../../lib/api/client';
import { sharedStyles as s, theme } from '../../theme';
import { parseAcademicProfile, type AcademicProfileView } from './academicData';
const sample: AcademicProfileView = { courses: [
  { course_id: 'demo-dsa', title: 'Data structures', import_status: 'ready', missing_sources: [] },
  { course_id: 'demo-prob', title: 'Probability', import_status: 'needs_review', missing_sources: ['Lecture slides'] },
  { course_id: 'demo-acct', title: 'Accounting', import_status: 'ready', missing_sources: [] },
], units: [
  { course_id: 'demo-dsa', title: 'Heaps and treaps' }, { course_id: 'demo-dsa', title: 'Linked lists' },
  { course_id: 'demo-prob', title: 'Distributions and Bayes' }, { course_id: 'demo-acct', title: 'Statements and cash flow' },
], assessments: [] };
interface Connection { status: 'connected' | 'disconnected' | 'reconnect_required' | 'error'; institution_origin?: string; last_sync_at?: string | null; job_id?: string }
export function CoursesScreen() {
  const { mode, api } = useAuth(); const demo = mode === 'preview';
  const [profile, setProfile] = useState<AcademicProfileView | null>(demo ? sample : null);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [token, setToken] = useState('');
  const tokenInput = useRef<React.ComponentRef<typeof TextInput>>(null);
  const [preparation, setPreparation] = useState<{academic_generation_configured: boolean; video_generation_enabled?: boolean; imports_and_lessons: Record<string, number>; videos: Record<string, number>} | null>(null);
  const [job, setJob] = useState<{state: string} | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false); const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null); const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(async () => {
    if (demo) return;
    setLoading(true); setError(null);
    try {
      const [conn, data] = await Promise.all([api.request<Connection>('/v1/canvas/connection'), api.request<unknown>('/v1/academics/profile').catch(error => { if (error instanceof ApiError && error.status === 404) return null; throw error; })]);
      if (!['connected', 'disconnected', 'reconnect_required', 'error'].includes(conn.status)) throw new Error('Unable to read Canvas status. Please retry.');
      setPreparation(await api.request('/v1/preparation'));
      setConnection(conn); if (conn.job_id) setJob(await api.request<{state: string}>(`/v1/academics/jobs/${conn.job_id}`)); setProfile(data === null ? null : parseAcademicProfile(data));
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'Unable to load courses. Please retry.'); }
    finally { setLoading(false); }
  }, [api, demo]);
  useEffect(() => { void load(); const listener = AppState.addEventListener('change', state => { if (state === 'active') void load(); }); return () => listener.remove(); }, [load]);
  useEffect(() => { if (demo || connection?.status !== 'connected') return; const timer = setInterval(() => { if (AppState.currentState === 'active') void load(); }, 10000); return () => clearInterval(timer); }, [demo, connection?.status, load]);
  async function connect() {
    if (demo) { setNotice('Sign in to connect your own Canvas courses. These cards are a sample semester.'); return; }
    if (token.trim().length < 10) { setNotice('Paste your Canvas personal access token below, then save it.'); tokenInput.current?.focus(); return; }
    setBusy(true); setError(null);
    try {
      await api.request('/v1/canvas/token', { method: 'POST', body: { token: token.trim() }, headers: { 'Idempotency-Key': Crypto.randomUUID() } });
      setToken(''); setNotice('Canvas connected. Your courses and lessons are preparing in the background.'); await load();
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'Canvas connection failed.'); } finally { setBusy(false); }
  }

  async function sync() {
    setBusy(true); setError(null);
    try { await api.request('/v1/canvas/sync', { method: 'POST', headers: { 'Idempotency-Key': Crypto.randomUUID() } }); setNotice('Sync requested. Pull to refresh as your courses become ready.'); }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'Sync failed. Please retry.'); } finally { setBusy(false); }
  }
  async function retryPreparation() {
    setBusy(true); setError(null);
    try { const result = await api.request<{queued_jobs: number}>('/v1/preparation/retry', { method: 'POST', headers: { 'Idempotency-Key': Crypto.randomUUID() } }); setNotice(`${result.queued_jobs} preparation jobs queued for retry.`); await load(); }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'Unable to retry preparation.'); } finally { setBusy(false); }
  }
  const accents = [theme.colors.accent, theme.colors.coral, theme.colors.success];
  return <SafeAreaView style={s.screen} edges={['top']}><ScrollView refreshControl={<RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={theme.colors.accent} />} contentContainerStyle={styles.content}>
    <Text accessibilityRole="header" style={s.title}>Courses</Text>
    <View style={styles.summary}><Ionicons name="school-outline" size={30} color={theme.colors.accent} /><View style={{ flex: 1, gap: 6 }}><Text style={styles.heading}>{profile?.courses.length ?? 0} {demo ? 'sample courses' : 'courses'}</Text><Text style={s.subtitle}>{demo ? 'Explore a synthetic semester.' : 'Imported from Canvas'}</Text></View></View>
    {!demo && loading && <ActivityIndicator color={theme.colors.accent} />}
    {error && <View style={s.card}><Text accessibilityRole="alert" style={styles.error}>{error}</Text><Button title="Retry courses" secondary onPress={() => void load()} /></View>}
    <View style={[s.card, { gap: 12 }]}><Text style={styles.heading}>{connection?.status === 'connected' ? 'Canvas is connected' : connection?.status === 'reconnect_required' ? 'Reconnect Canvas' : 'Connect Canvas'}</Text><Text style={s.subtitle}>{connection?.status === 'connected' ? 'Refresh to bring in your latest coursework.' : 'Connect Canvas for lessons from your courses. You can keep scrolling while they prepare.'}</Text><Button title={connection?.status === 'connected' ? 'Sync courses' : 'Connect Canvas'} busy={busy} onPress={() => void (connection?.status === 'connected' ? sync() : connect())} /></View>
    {!demo && connection?.status !== 'connected' && <View style={[s.card, { gap: 12 }]}><Text style={s.subtitle}>In Canvas, open Account → Settings → New Access Token. Paste your token here to connect your courses.</Text><TextInput ref={tokenInput} accessibilityLabel="Canvas personal access token" secureTextEntry autoCapitalize="none" autoCorrect={false} value={token} onChangeText={setToken} placeholder="Canvas personal access token" placeholderTextColor={theme.colors.muted} style={s.input} /><Button title="Save Canvas token" busy={busy} onPress={() => void connect()} /></View>}
    {preparation && <View style={[s.card, { gap: 8 }]}><Text style={styles.heading}>Preparing your feed</Text>{preparation.video_generation_enabled === false && <Text style={s.subtitle}>New video generation is paused to conserve credits. Ready videos remain available.</Text>}{!preparation.academic_generation_configured && <Text style={s.subtitle}>Lesson generation is waiting for the demo host to configure Gemini. Your connections stay saved.</Text>}<Text style={s.subtitle}>{Object.entries(preparation.imports_and_lessons).map(([state, count]) => `${count} ${state.replaceAll('_', ' ')}`).join(' · ') || 'Connect Canvas to start preparing lessons.'}</Text><Text style={s.subtitle}>Videos: {Object.entries(preparation.videos).map(([state, count]) => `${count} ${state.replaceAll('_', ' ')}`).join(' · ') || 'Waiting for course topics'}</Text>{((preparation.imports_and_lessons.failed ?? 0) + (preparation.videos.failed ?? 0)) > 0 && <Button title="Retry failed preparation" busy={busy} secondary onPress={() => void retryPreparation()} />}</View>}
    {job && <Text style={s.subtitle}>Course import: {job.state.replaceAll('_', ' ')}</Text>}
    {!demo && connection?.status === 'connected' && <Button title="Disconnect Canvas" secondary onPress={() => { void api.request('/v1/canvas/connection', { method: 'DELETE' }).then(() => load()).catch(problem => setError(problem.message)); }} />}
    {!demo && <InstagramConnection />}
    {notice && <Text accessibilityRole="alert" style={s.subtitle}>{notice}</Text>}
    <View style={styles.section}><Text style={styles.heading}>Your syllabus</Text>{demo && <Text style={styles.badge}>SAMPLE DATA</Text>}</View>
    {profile?.courses.map((course, i) => <View key={course.course_id} style={styles.course}>
      <Pressable accessibilityRole="button" accessibilityState={{ expanded: expanded === course.course_id }} accessibilityLabel={course.title || 'Course'} onPress={() => setExpanded(expanded === course.course_id ? null : course.course_id)} style={styles.courseHeader}><View style={[styles.dot, { backgroundColor: accents[i % accents.length] }]} /><View style={{ flex: 1, gap: 5 }}><Text style={styles.heading}>{course.title || 'Untitled course'}</Text><Text style={styles.detail}>{course.import_status.replaceAll('_', ' ')}</Text></View><Ionicons name={expanded === course.course_id ? 'chevron-up' : 'chevron-down'} size={20} color={theme.colors.muted} /></Pressable>
      {expanded === course.course_id && <View style={styles.topics}>{profile.units.filter(unit => unit.course_id === course.course_id).map((unit, j) => <View key={j} style={styles.topic}><Ionicons name="ellipse-outline" size={16} color={accents[i % accents.length]} /><Text style={s.subtitle}>{unit.title}</Text></View>)}{profile.assessments.filter(item => item.course_id === course.course_id).map((item, j) => <View key={j} style={styles.topic}><Ionicons name="calendar-outline" size={18} color={theme.colors.coral} /><View style={{ flex: 1 }}><Text style={styles.heading}>{item.title}</Text><Text style={styles.detail}>{item.dateLabel}</Text></View></View>)}{course.missing_sources.length > 0 && <Text style={styles.error}>Missing: {course.missing_sources.join(', ')}</Text>}<Text style={styles.detail}>Coverage and quiz progress will appear when learning activity is available.</Text></View>}
    </View>)}
    {!profile?.courses.length && !loading && <Text style={s.subtitle}>No imported courses yet. Your feed is ready whenever you are.</Text>}
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({ content: { padding: 22, gap: 18, maxWidth: 640, width: '100%', alignSelf: 'center', paddingBottom: 36 }, summary: { backgroundColor: '#211B35', padding: 24, borderRadius: 24, flexDirection: 'row', alignItems: 'center', gap: 18 }, heading: { fontFamily: theme.fonts.bold, fontSize: 17, color: theme.colors.text }, section: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }, badge: { color: theme.colors.accent, fontFamily: theme.fonts.bold, fontSize: 11 }, course: { backgroundColor: theme.colors.surface, borderRadius: 22, borderWidth: 1, borderColor: theme.colors.elevated }, courseHeader: { minHeight: 86, flexDirection: 'row', alignItems: 'center', gap: 12, padding: 18 }, dot: { width: 10, height: 10, borderRadius: 5 }, topics: { padding: 18, paddingTop: 0, gap: 16 }, topic: { flexDirection: 'row', alignItems: 'center', gap: 10 }, detail: { fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 13, lineHeight: 19 }, error: { fontFamily: theme.fonts.body, color: theme.colors.danger, fontSize: 14, lineHeight: 20 } });
