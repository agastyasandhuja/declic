// Course profile review + correction (owner: Amogh).
//
// Shows units, assessments (with honest date/evidence display) and the Gemini
// lesson plan. The student can correct an exam date or scope; that produces a
// new profile revision via api.applyCorrections. No invented dates: a cleared
// date stays unknown, and a typed date is marked "you confirmed".
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { AcademicsApiClient, CourseProfileDetail } from '../api/types';
import type { AcademicsTheme } from '../theme';
import { defaultTheme } from '../theme';
import {
  buildCorrections, formatAcademicDate, isValidDateInput, lessonExamLabel,
} from '../viewmodel/format';
import { StatusBadge } from './StatusBadge';

export interface CourseProfileProps {
  api: AcademicsApiClient;
  courseId: string;
  profileRevision: number;
  theme?: AcademicsTheme;
  onBack?: () => void;
}

export function CourseProfile({ api, courseId, profileRevision, theme = defaultTheme, onBack }: CourseProfileProps) {
  const [detail, setDetail] = useState<CourseProfileDetail | null>(null);
  const [edits, setEdits] = useState<Record<string, { date?: string | null }>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api.getCourseProfile(courseId).then((d) => alive && setDetail(d)).catch((e) => alive && setError(String(e)));
    return () => { alive = false; };
  }, [api, courseId]);

  async function save() {
    if (!detail) return;
    const original = detail.assessments.map((a) => ({ assessmentId: a.assessmentId, date: a.scheduled.date, scopeStatus: a.scopeStatus }));
    const corrections = buildCorrections(original, edits);
    if (corrections.length === 0) { setError('No changes to save.'); return; }
    setBusy(true); setError(null);
    try {
      const updated = await api.applyCorrections(courseId, profileRevision, corrections);
      setDetail(updated); setEdits({});
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  if (error && !detail) return <Text style={{ color: theme.colors.bad }}>{error}</Text>;
  if (!detail) return <ActivityIndicator color={theme.colors.accent} style={{ marginTop: 24 }} />;

  const c = detail.course;
  const invalidEdit = Object.values(edits).some((e) => e.date != null && !isValidDateInput(e.date));

  return (
    <ScrollView contentContainerStyle={{ gap: 14, padding: 2 }}>
      <View style={styles.header}>
        {onBack && <Pressable onPress={onBack}><Text style={{ color: theme.colors.accent }}>‹ Courses</Text></Pressable>}
        <Text style={[styles.h1, { color: theme.colors.text }]}>{c.title ?? c.courseId}</Text>
      </View>

      <Section title="Units" theme={theme}>
        {detail.units.length === 0 && <Muted theme={theme}>No units extracted yet.</Muted>}
        {detail.units.map((u) => (
          <View key={u.unitId} style={{ marginBottom: 8 }}>
            <Text style={[styles.rowTitle, { color: theme.colors.text }]}>{u.order}. {u.title}</Text>
            {u.objectives.map((o, i) => <Text key={i} style={[styles.obj, { color: theme.colors.textMuted }]}>• {o}</Text>)}
          </View>
        ))}
      </Section>

      <Section title="Exams & assessments" theme={theme}>
        {detail.assessments.map((a) => {
          const edit = edits[a.assessmentId];
          const value = edit?.date ?? (a.scheduled.date ?? '');
          return (
            <View key={a.assessmentId} style={{ marginBottom: 10 }}>
              <View style={styles.row}>
                <Text style={[styles.rowTitle, { color: theme.colors.text }]}>{a.title} ({a.kind})</Text>
                <StatusBadge theme={theme} label={a.scopeStatus} tone={a.scopeStatus === 'explicit' ? 'ok' : 'muted'} />
              </View>
              <Text style={[styles.obj, { color: theme.colors.textMuted }]}>{formatAcademicDate(a.scheduled)}</Text>
              <TextInput
                value={value}
                onChangeText={(t) => setEdits((p) => ({ ...p, [a.assessmentId]: { date: t === '' ? null : t } }))}
                placeholder="YYYY-MM-DD (confirm the exam date)"
                placeholderTextColor={theme.colors.muted}
                autoCapitalize="none"
                style={[styles.input, { color: theme.colors.text, borderColor: edit && value && !isValidDateInput(value) ? theme.colors.bad : theme.colors.border, borderRadius: theme.radius }]}
              />
            </View>
          );
        })}
      </Section>

      <Section title="Planned lessons" theme={theme}>
        {detail.lessons.map((l) => (
          <View key={l.lessonRequestId} style={{ marginBottom: 8 }}>
            <View style={styles.row}>
              <Text style={[styles.rowTitle, { color: theme.colors.text }]}>{l.title}</Text>
              <Text style={[styles.obj, { color: theme.colors.textMuted }]}>{l.targetDurationSeconds}s</Text>
            </View>
            <Text style={[styles.obj, { color: theme.colors.textMuted }]}>{l.learningGoal}</Text>
            <StatusBadge theme={theme} label={lessonExamLabel(l)}
              tone={l.evidenceStatus === 'suggested_practice' ? 'muted' : l.examScopeStatus === 'explicit' ? 'ok' : 'warn'} />
          </View>
        ))}
      </Section>

      {error && <Text style={{ color: theme.colors.bad }}>{error}</Text>}
      <Pressable disabled={busy || invalidEdit} onPress={save}
        style={[styles.save, { backgroundColor: invalidEdit ? theme.colors.muted : theme.colors.accent, borderRadius: theme.radius }]}>
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveText}>Save corrections</Text>}
      </Pressable>
    </ScrollView>
  );
}

function Section({ title, theme, children }: { title: string; theme: AcademicsTheme; children: React.ReactNode }) {
  return (
    <View style={[styles.section, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border, borderRadius: theme.radius }]}>
      <Text style={[styles.h2, { color: theme.colors.text }]}>{title}</Text>
      {children}
    </View>
  );
}
function Muted({ theme, children }: { theme: AcademicsTheme; children: React.ReactNode }) {
  return <Text style={{ color: theme.colors.textMuted }}>{children}</Text>;
}

const styles = StyleSheet.create({
  header: { gap: 6 },
  h1: { fontSize: 22, fontWeight: '800' },
  section: { borderWidth: 1, padding: 14 },
  h2: { fontSize: 16, fontWeight: '700', marginBottom: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  rowTitle: { fontSize: 15, fontWeight: '600', flexShrink: 1 },
  obj: { fontSize: 13, marginTop: 2 },
  input: { borderWidth: 1, paddingHorizontal: 10, paddingVertical: 8, marginTop: 6 },
  save: { padding: 14, alignItems: 'center', marginTop: 4 },
  saveText: { color: '#fff', fontWeight: '700' },
});
