// Per-course import progress (owner: Amogh).
//
// Shows readiness for each course separately (ready / needs review / error),
// so a student sees partial progress while some courses are still processing.
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { CourseSummary } from '../api/types';
import type { AcademicsTheme } from '../theme';
import { defaultTheme } from '../theme';
import { importStatusLabel, importStatusTone } from '../viewmodel/format';
import { StatusBadge } from './StatusBadge';

export interface ImportProgressProps {
  courses: CourseSummary[];
  theme?: AcademicsTheme;
}

export function ImportProgress({ courses, theme = defaultTheme }: ImportProgressProps) {
  const ready = courses.filter((c) => c.importStatus === 'ready').length;
  return (
    <View style={[styles.card, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border, borderRadius: theme.radius }]}>
      <Text style={[styles.title, { color: theme.colors.text }]}>
        Preparing your courses — {ready}/{courses.length} ready
      </Text>
      {courses.map((c) => (
        <View key={c.courseId} style={styles.row}>
          <Text style={[styles.name, { color: theme.colors.textMuted }]} numberOfLines={1}>
            {c.title ?? c.courseId}
          </Text>
          <StatusBadge theme={theme} label={importStatusLabel(c.importStatus)} tone={importStatusTone(c.importStatus)} />
        </View>
      ))}
      {courses.some((c) => c.missingSources.length > 0) && (
        <Text style={[styles.note, { color: theme.colors.textMuted }]}>
          Some courses are missing a syllabus; lessons use their assignment schedule instead.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, padding: 14, gap: 8 },
  title: { fontSize: 15, fontWeight: '700' },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  name: { fontSize: 14, flexShrink: 1 },
  note: { fontSize: 12, marginTop: 4 },
});
