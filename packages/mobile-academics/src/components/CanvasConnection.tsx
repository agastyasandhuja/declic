// Canvas connection panel (owner: Amogh).
//
// Props injected by Adi: the api client and theme. This component owns no
// secrets and does no navigation. It shows status and lets the student connect,
// sync, or disconnect. Connection modes come from the backend (oauth when a
// developer key exists; developer_token / upload otherwise).
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import type { AcademicsApiClient, CanvasConnectionSummary, ConnectionMode } from '../api/types';
import type { AcademicsTheme } from '../theme';
import { defaultTheme } from '../theme';
import { StatusBadge } from './StatusBadge';

const MODE_LABEL: Record<ConnectionMode, string> = {
  oauth: 'Sign in with UMass',
  developer_token: 'Connect with token',
  upload: 'Upload course files',
};

export interface CanvasConnectionProps {
  api: AcademicsApiClient;
  theme?: AcademicsTheme;
  onConnected?: (summary: CanvasConnectionSummary) => void;
  onSyncStarted?: (jobId: string) => void;
}

export function CanvasConnection({ api, theme = defaultTheme, onConnected, onSyncStarted }: CanvasConnectionProps) {
  const [summary, setSummary] = useState<CanvasConnectionSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api.getConnection().then((s) => alive && setSummary(s)).catch((e) => alive && setError(String(e)));
    return () => { alive = false; };
  }, [api]);

  async function run(fn: () => Promise<CanvasConnectionSummary | { jobId: string }>, isSync = false) {
    setBusy(true); setError(null);
    try {
      const result = await fn();
      if (isSync && 'jobId' in result) { onSyncStarted?.(result.jobId); return; }
      const s = result as CanvasConnectionSummary;
      setSummary(s);
      if (s.status === 'connected') onConnected?.(s);
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }

  const connected = summary?.status === 'connected';
  return (
    <View style={[styles.card, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border, borderRadius: theme.radius }]}>
      <View style={styles.row}>
        <Text style={[styles.title, { color: theme.colors.text }]}>Canvas</Text>
        {summary && <StatusBadge theme={theme} label={summary.status.replace('_', ' ')}
          tone={connected ? 'ok' : summary.status === 'error' ? 'bad' : 'muted'} />}
      </View>
      {summary?.institutionOrigin && (
        <Text style={[styles.muted, { color: theme.colors.textMuted }]}>{summary.institutionOrigin}</Text>
      )}
      {summary?.lastSyncAt && (
        <Text style={[styles.muted, { color: theme.colors.textMuted }]}>Last synced {summary.lastSyncAt}</Text>
      )}
      {busy && <ActivityIndicator color={theme.colors.accent} style={{ marginVertical: 8 }} />}
      {error && <Text style={{ color: theme.colors.bad, marginTop: 6 }}>{error}</Text>}

      <View style={styles.actions}>
        {!connected && (summary?.availableModes ?? []).map((mode) => (
          <Pressable key={mode} disabled={busy} onPress={() => run(() => api.connect(mode))}
            style={[styles.btn, { backgroundColor: theme.colors.accent, borderRadius: theme.radius }]}>
            <Text style={styles.btnText}>{MODE_LABEL[mode]}</Text>
          </Pressable>
        ))}
        {connected && (
          <>
            <Pressable disabled={busy} onPress={() => run(() => api.sync(), true)}
              style={[styles.btn, { backgroundColor: theme.colors.accent, borderRadius: theme.radius }]}>
              <Text style={styles.btnText}>Sync courses</Text>
            </Pressable>
            <Pressable disabled={busy} onPress={() => run(() => api.disconnect())}
              style={[styles.btn, styles.btnGhost, { borderColor: theme.colors.border, borderRadius: theme.radius }]}>
              <Text style={[styles.btnText, { color: theme.colors.textMuted }]}>Disconnect</Text>
            </Pressable>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, padding: 16, gap: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 18, fontWeight: '700' },
  muted: { fontSize: 13 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  btn: { paddingHorizontal: 14, paddingVertical: 10 },
  btnGhost: { backgroundColor: 'transparent', borderWidth: 1 },
  btnText: { color: '#fff', fontWeight: '600' },
});
