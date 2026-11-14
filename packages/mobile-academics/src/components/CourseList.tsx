// Course list ordered by real-time urgency (owner: Amogh).
import React from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import type { CourseSummary } from '../api/types';
import type { AcademicsTheme } from '../theme';
import { defaultTheme } from '../theme';
import { importStatusLabel, importStatusTone, sortByUrgency, urgencyLabel } from '../viewmodel/format';
import { StatusBadge } from './StatusBadge';

export interface CourseListProps {
  courses: CourseSummary[];
  theme?: AcademicsTheme;
  onSelectCourse?: (courseId: string) => void;
}

export function CourseList({ courses, theme = defaultTheme, onSelectCourse }: CourseListProps) {
  const ordered = sortByUrgency(courses);
  return (
    <FlatList
      data={ordered}
      keyExtractor={(c) => c.courseId}
      contentContainerStyle={{ gap: 10, padding: 2 }}
      ListEmptyComponent={<Text style={{ color: theme.colors.textMuted }}>No courses yet. Connect Canvas to import.</Text>}
      renderItem={({ item }) => {
        const urgency = urgencyLabel(item);
        return (
          <Pressable onPress={() => onSelectCourse?.(item.courseId)}
            style={[styles.card, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border, borderRadius: theme.radius }]}>
            <View style={styles.row}>
              <Text style={[styles.title, { color: theme.colors.text }]} numberOfLines={1}>
                {item.title ?? item.courseId}
              </Text>
              <StatusBadge theme={theme} label={importStatusLabel(item.importStatus)} tone={importStatusTone(item.importStatus)} />
            </View>
            {item.term && <Text style={[styles.muted, { color: theme.colors.textMuted }]}>{item.term}</Text>}
            {urgency && (
              <Text style={[styles.urgency, { color: item.timing && item.timing.daysUntilNext !== null && item.timing.daysUntilNext <= 3 ? theme.colors.warn : theme.colors.textMuted }]}>
                {urgency}
              </Text>
            )}
          </Pressable>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, padding: 14, gap: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  title: { fontSize: 16, fontWeight: '700', flexShrink: 1 },
  muted: { fontSize: 13 },
  urgency: { fontSize: 14, fontWeight: '600', marginTop: 2 },
});
