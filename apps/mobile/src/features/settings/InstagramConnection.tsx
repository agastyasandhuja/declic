import React, { useEffect, useState } from 'react';
import { AppState, Text, TextInput, View } from 'react-native';
import { useAuth } from '../../state/AuthProvider';
import { Button } from '../../components/Button';
import { sharedStyles as s, theme } from '../../theme';
export function InstagramConnection() {
  const { api } = useAuth(); const [status, setStatus] = useState('disconnected');
  const [username, setUsername] = useState(''); const [password, setPassword] = useState(''); const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState<string | null>(null);
  const load = () => api.request<{status: string}>('/v1/instagram/connection').then(r => setStatus(r.status));
  useEffect(() => { let active = true; const refresh = () => { if (active && AppState.currentState === 'active') void load().catch(problem => setMessage(problem.message)); }; refresh(); const timer = setInterval(refresh, 15000); const listener = AppState.addEventListener('change', state => { if (state === 'active') refresh(); }); return () => { active = false; clearInterval(timer); listener.remove(); }; }, [api]);
  async function connect() {
    if (!/^[A-Za-z0-9_.]{1,30}$/.test(username.trim()) || !password) { setMessage('Enter your Instagram username and password.'); return; }
    if (code && !/^\d{6}$/.test(code.trim())) { setMessage('Enter the complete verification code, or leave it empty.'); return; }
    setBusy(true); setMessage(null);
    try { await api.request('/v1/instagram/connect', { method: 'POST', timeoutMs: 60000, body: { username: username.trim(), password, ...(code ? { verification_code: code.trim() } : {}) } }); setPassword(''); setCode(''); await load(); setMessage('Connected. Reels are preparing in the background.'); }
    catch (problem) { setMessage(problem instanceof Error ? problem.message : 'Instagram connection failed.'); }
    finally { setBusy(false); }
  }
  const input = { color: theme.colors.text, borderColor: theme.colors.elevated, borderWidth: 1, borderRadius: 12, padding: 14 };
  return <View style={[s.card, { gap: 12 }]}><Text style={s.eyebrow}>INSTAGRAM</Text><Text style={s.subtitle}>{status === 'connected' ? 'Your Instagram session is saved.' : status === 'reconnect_required' ? 'Instagram needs attention. Open Instagram on your phone, then reconnect here.' : 'Connect Instagram to bring Reels into your feed.'}</Text>
    {status !== 'connected' ? <><TextInput accessibilityLabel="Instagram username" value={username} onChangeText={setUsername} autoCapitalize="none" autoCorrect={false} placeholder="Username" placeholderTextColor={theme.colors.muted} style={input} /><TextInput accessibilityLabel="Instagram password" value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" autoCorrect={false} placeholder="Password" placeholderTextColor={theme.colors.muted} style={input} /><TextInput accessibilityLabel="Instagram authenticator code" value={code} onChangeText={setCode} secureTextEntry keyboardType="number-pad" placeholder="Authenticator code, if requested" placeholderTextColor={theme.colors.muted} style={input} /><Button title="Connect Instagram" busy={busy} onPress={() => void connect()} /></> : <Button title="Disconnect Instagram" secondary onPress={() => { void api.request('/v1/instagram/connection', { method: 'DELETE' }).then(load).catch(problem => setMessage(problem.message)); }} />}
    {message && <Text accessibilityRole="alert" style={s.subtitle}>{message}</Text>}
  </View>;
}
