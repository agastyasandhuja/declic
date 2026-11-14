// Academics feature screen (owner: Amogh).
//
// Composes the academics components into one screen Adi can mount at a route he
// owns. It does NOT create a navigation container or an auth store: it switches
// between the course list and a course detail with local state, and receives the
// api client, identity and theme as props. Adi wires routing and provides these.
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { AcademicsApiClient, CourseSummary, Identity } from '../api/types';
import type { AcademicsTheme } from '../theme';
import { defaultTheme } from '../theme';
import { CanvasConnection } from '../components/CanvasConnection';
import { CourseList } from '../components/CourseList';
import { CourseProfile } from '../components/CourseProfile';
import { ImportProgress } from '../components/ImportProgress';

export interface AcademicsScreenProps {
  api: AcademicsApiClient;
  identity: Identity;        // current app user; the client authenticates as them
  theme?: AcademicsTheme;
  profileRevision?: number;  // latest known profile revision, for corrections
}

export function AcademicsScreen({ api, identity, theme = defaultTheme, profileRevision = 1 }: AcademicsScreenProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    try { setCourses(await api.getCourses()); } finally { setRefreshing(false); }
  }, [api]);

  useEffect(() => { void load(); }, [load]);

  if (selected) {
    return (
      <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
        <CourseProfile api={api} courseId={selected} profileRevision={profileRevision}
          theme={theme} onBack={() => setSelected(null)} />
      </View>
    );
  }

  const anyProcessing = courses.some((c) => c.importStatus !== 'ready' && c.importStatus !== 'error');
  return (
    <ScrollView
      style={[styles.root, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={{ gap: 14, padding: 16 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} tintColor={theme.colors.accent} />}
    >
      <Text style={[styles.h1, { color: theme.colors.text }]}>Your courses</Text>
      <Text style={[styles.sub, { color: theme.colors.textMuted }]} accessibilityLabel={`signed in as ${identity.userId}`}>
        Lessons are prioritized by what's due soonest.
      </Text>
      <CanvasConnection api={api} theme={theme} onConnected={load} onSyncStarted={load} />
      {anyProcessing && courses.length > 0 && <ImportProgress courses={courses} theme={theme} />}
      <CourseList courses={courses} theme={theme} onSelectCourse={setSelected} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  h1: { fontSize: 24, fontWeight: '800' },
  sub: { fontSize: 14 },
});
