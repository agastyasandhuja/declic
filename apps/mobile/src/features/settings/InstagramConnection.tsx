import React, { useEffect, useState } from 'react';
import { AppState, StyleSheet, Text, TextInput, View } from 'react-native';
import { Button } from '../../components/Button';
import { useAuth } from '../../state/AuthProvider';
import { sharedStyles as s, theme } from '../../theme';

export function InstagramConnection() {
  const { api } = useAuth();
  const [status, setStatus] = useState('disconnected');
  const [username, setUsername] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [editing, setEditing] = useState(false);
  const connected = status === 'connected';
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = () => api.request<{ status: string }>('/v1/instagram/connection').then(response => setStatus(response.status));
  useEffect(() => {
    let active = true;
    const refresh = () => {
      if (active && AppState.currentState === 'active') {
        void load().catch(() => setMessage('Unable to check the Instagram connection.'));
      }
    };
    refresh();
    const timer = setInterval(refresh, 15000);
    const listener = AppState.addEventListener('change', state => { if (state === 'active') refresh(); });
    return () => { active = false; clearInterval(timer); listener.remove(); };
  }, [api]);

  async function connect() {
    const name = username.trim();
    const value = sessionId.trim();
    if (!/^[A-Za-z0-9_.]{1,30}$/.test(name)) {
      setMessage('Enter your Instagram username.');
      return;
    }
    if (value.length < 31 || value.length > 16384 || !/^\d\S+$/.test(value)) {
      setMessage('Paste the value of the sessionid cookie from an Instagram session you own.');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.request<{ status: 'connected' }>('/v1/instagram/browser-session', {
        method: 'POST',
        timeoutMs: 60000,
        body: { username: name, session_id: value },
      });
      setSessionId('');
      setEditing(false);
      setStatus(result.status);
      setMessage(editing ? 'Instagram session updated.' : 'Connected. Reels are preparing in the background.');
    } catch {
      setMessage('Unable to verify the Instagram session. Check that the cookie is current and belongs to this username, then retry.');
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setMessage(null);
    try {
      await api.request('/v1/instagram/connection', { method: 'DELETE' });
      await load();
    } catch {
      setMessage('Unable to disconnect Instagram. Please retry.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={[s.card, styles.card]}>
      <Text accessibilityRole="header" style={styles.heading}>Instagram</Text>
      <Text style={s.subtitle}>
        {connected ? 'Your Instagram session is connected.' : status === 'reconnect_required' ? 'Reconnect with a current session cookie.' : 'Connect your Instagram session for this demo.'}
      </Text>
      {connected && !editing ? (
        <>
          <Button title="Update session cookie" disabled={busy} onPress={() => { setMessage(null); setEditing(true); }} />
          <Button title="Disconnect Instagram" busy={busy} secondary onPress={() => void disconnect()} />
        </>
      ) : (
        <>
          <Text style={s.subtitle}>Sign in to Instagram in your browser, then copy the value of the sessionid cookie from its storage inspector.</Text>
          <TextInput
            accessibilityLabel="Instagram username"
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="off"
            editable={!busy}
            maxLength={30}
            placeholder="Instagram username"
            placeholderTextColor={theme.colors.muted}
            style={s.input}
          />
          <TextInput
            accessibilityLabel="Instagram session cookie"
            value={sessionId}
            onChangeText={setSessionId}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="off"
            editable={!busy}
            maxLength={16384}
            placeholder="Paste sessionid value"
            placeholderTextColor={theme.colors.muted}
            style={s.input}
          />
          <Button title={editing ? 'Save session cookie' : 'Connect Instagram'} busy={busy} onPress={() => void connect()} />
          {editing && <Button title="Cancel" disabled={busy} secondary onPress={() => { setSessionId(''); setMessage(null); setEditing(false); }} />}
        </>
      )}
      {message && <Text accessibilityRole="alert" style={s.subtitle}>{message}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { gap: 12 },
  heading: { fontFamily: theme.fonts.bold, fontSize: 17, color: theme.colors.text },
});
