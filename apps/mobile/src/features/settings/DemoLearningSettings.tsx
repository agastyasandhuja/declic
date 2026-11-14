import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Switch, Text, View } from 'react-native';
import * as Crypto from 'expo-crypto';
import type { ApiClient } from '../../lib/api/client';
import { Button } from '../../components/Button';
import { sharedStyles as s, theme } from '../../theme';
interface DemoCourse { course_id: string; title: string; objectives: { objective_id: string; title: string }[]; video_count: number }

export function DemoLearningSettings({ api, onChanged }: { api: ApiClient; onChanged(): void }) {
  const [enabled, setEnabled] = useState<boolean | null>(null); const [courses, setCourses] = useState<DemoCourse[]>([]);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null); const [attempt, setAttempt] = useState(0);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true; const abort = new AbortController();
    void api.request<{ schema_version: string; demo_mode: boolean }>('/v1/learning/settings', { signal: abort.signal }).then(value => {
      if (abort.signal.aborted) return;
      if (value.schema_version !== '1' || typeof value.demo_mode !== 'boolean') throw new Error('Invalid settings');
      setEnabled(value.demo_mode);
    }).catch(() => { if (!abort.signal.aborted) setError('Unable to load demo settings.'); });
    return () => { mounted.current = false; abort.abort(); };
  }, [api, attempt]);
  useEffect(() => {
    if (!enabled) { setCourses([]); return; }
    const abort = new AbortController();
    void api.request<{ courses: DemoCourse[] }>('/v1/learning/demo-catalog', { signal: abort.signal }).then(value => {
      if (abort.signal.aborted) return;
      if (!Array.isArray(value.courses) || value.courses.some(course => typeof course.course_id !== 'string' || typeof course.title !== 'string' || !Number.isSafeInteger(course.video_count) || course.video_count < 0)) throw new Error('Invalid demo catalog');
      setCourses(value.courses);
    }).catch(() => { if (!abort.signal.aborted) setError('The demo catalog is unavailable right now. Your setting is saved.'); });
    return () => abort.abort();
  }, [api, enabled, attempt]);
  async function change(value: boolean) {
    setBusy(true); setError(null);
    try {
      const result = await api.request<{ demo_mode: boolean }>('/v1/learning/settings', { method: 'PATCH', headers: { 'Idempotency-Key': Crypto.randomUUID() }, body: { demo_mode: value } });
      if (typeof result.demo_mode !== 'boolean') throw new Error('Invalid setting');
      if (mounted.current) setEnabled(result.demo_mode);
      onChanged(); // Remount the feed; mode changes withdraw old cards and gates.
    } catch { if (mounted.current) setError('Unable to update demo mode. Please retry.'); }
    finally { if (mounted.current) setBusy(false); }
  }
  return <View style={[s.card, { gap: 12 }]}><View style={styles.row}><View style={{ flex: 1, gap: 5 }}><Text accessibilityRole="header" style={styles.heading}>Demo learning library</Text><Text style={s.subtitle}>Mix shared demo lessons into your feed without connecting Canvas.</Text></View>{enabled === null ? <ActivityIndicator color={theme.colors.accent} /> : <Switch accessibilityLabel="Demo learning library" value={enabled} disabled={busy} onValueChange={value => void change(value)} trackColor={{ false: theme.colors.elevated, true: theme.colors.accent }} />}</View>
    {busy && <ActivityIndicator color={theme.colors.accent} />}
    {enabled && courses.map(course => <View key={course.course_id} style={{ gap: 3 }}><Text style={styles.heading}>{course.title}</Text><Text style={s.subtitle}>{course.video_count} ready {course.video_count === 1 ? 'video' : 'videos'}</Text></View>)}
    {error && <><Text accessibilityRole="alert" style={s.subtitle}>{error}</Text><Button title="Retry demo settings" secondary onPress={() => { setError(null); setAttempt(value => value + 1); }} /></>}
  </View>;
}
const styles = StyleSheet.create({ row: { flexDirection: 'row', alignItems: 'center', gap: 12 }, heading: { fontFamily: theme.fonts.bold, fontSize: 16, color: theme.colors.text } });
