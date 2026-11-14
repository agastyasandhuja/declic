import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { AppState } from 'react-native';
import type { Session } from '@supabase/supabase-js';
import { supabase, clearSavedSession } from '../lib/auth/supabase';
import { config } from '../config';
import { createApiClient, type ApiClient } from '../lib/api/client';
import type { CurrentUser } from '../contracts/generated';
import demoUser from '../../../../fixtures/identity/current-user.json';

type Mode = 'loading' | 'signed_out' | 'signed_in' | 'preview';
interface AuthState {
  mode: Mode; user: CurrentUser | null; session: Session | null; api: ApiClient;
  error: string | null; enterPreview(): void; signOut(): Promise<void>; retryRestore(): void; resetSavedSession(): Promise<void>;
}
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: React.PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(null);
  const [mode, setMode] = useState<Mode>('loading');
  const [error, setError] = useState<string | null>(null);
  const [restoreRevision, setRestoreRevision] = useState(0);
  useEffect(() => {
    const client = supabase;
    if (!client) { setMode('signed_out'); return; }
    let alive = true;
    let observed = false;
    const { data } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (!alive || client !== supabase) return;
      observed = true;
      setSession(nextSession); setMode(nextSession ? 'signed_in' : 'signed_out'); setError(null);
    });
    client.auth.getSession().then(({ data: initial, error: problem }) => {
      if (!alive || client !== supabase) return;
      if (problem) { setError('Unable to restore your session. Retry or sign in again.'); setMode('signed_out'); }
      else if (!observed) { setSession(initial.session); setMode(initial.session ? 'signed_in' : 'signed_out'); }
    }).catch(() => { if (alive) { setError('Unable to read the saved session. Please retry.'); setMode('signed_out'); } });
    const updateRefresh = (state: string | null | undefined) => { void (state === 'active' ? client.auth.startAutoRefresh() : client.auth.stopAutoRefresh()).catch(() => { if (alive) setError('Unable to refresh your session. Check your connection and retry.'); }); };
    updateRefresh(AppState.currentState);
    const listener = AppState.addEventListener('change', updateRefresh);
    return () => { alive = false; data.subscription.unsubscribe(); listener.remove(); void client.auth.stopAutoRefresh(); };
  }, [restoreRevision]);

  const expireSession = useCallback(() => {
    setSession(null); setMode('signed_out'); setError('Your session has expired. Please sign in again.');
    void supabase?.auth.signOut({ scope: 'local' }).catch(() => undefined);
  }, []);
  const api = useMemo(() => createApiClient({
    baseUrl: config.apiBaseUrl,
    getAccessToken: async force => {
      if (!supabase || mode !== 'signed_in') return null;
      const result = force ? await supabase.auth.refreshSession() : await supabase.auth.getSession();
      // A dependency outage is retryable; only an invalid/missing session expires it.
      if (result.error) {
        if (result.error.name === 'AuthRetryableFetchError' || !result.error.status || result.error.status >= 500) throw result.error;
        return null;
      }
      return result.data.session?.access_token ?? null;
    },
    onUnauthorized: expireSession,
  }), [mode, expireSession]);
  const user: CurrentUser | null = mode === 'preview' ? demoUser : session ? {
    user_id: session.user.id, email: session.user.email ?? null,
    display_name: typeof session.user.user_metadata?.display_name === 'string' ? session.user.user_metadata.display_name : null,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', created_at: session.user.created_at,
  } : null;

  const value: AuthState = {
    mode, user, session, api, error,
    enterPreview: () => { if (config.previewEnabled) { setSession(null); setMode('preview'); setError(null); } },
    retryRestore: () => { setMode('loading'); setRestoreRevision(revision => revision + 1); },
    resetSavedSession: async () => {
      try {
        await clearSavedSession(); setSession(null); setError(null); setMode('signed_out'); setRestoreRevision(revision => revision + 1);
      } catch { setError('Unable to clear device storage. Retry before signing in.'); }
    },
    signOut: async () => {
      if (mode === 'signed_in' && supabase) {
        const { error: problem } = await supabase.auth.signOut({ scope: 'local' });
        if (problem) throw new Error('Unable to sign out. Check your connection and retry.');
      }
      setSession(null); setMode('signed_out'); setError(null);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('Feature components must be inside AuthProvider.');
  return value;
}
