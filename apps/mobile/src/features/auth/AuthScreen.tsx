import React, { useState, useRef } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../../lib/auth/supabase';
import { authConfigured, config } from '../../config';
import { useAuth } from '../../state/AuthProvider';
import { Button } from '../../components/Button';
import { Brand } from '../../components/Brand';
import { WelcomeScreen } from './WelcomeScreen';
import { sharedStyles as s, theme } from '../../theme';

export function AuthScreen() {
  const { enterPreview, error: restoreError, retryRestore, resetSavedSession } = useAuth();
  const [welcome, setWelcome] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const passwordRef = useRef<React.ComponentRef<typeof TextInput>>(null);
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState<string | null>(null); const [error, setError] = useState<string | null>(null);
  async function submit() {
    if (busy) return;
    setError(null); setMessage(null);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { setError('Enter a valid email address.'); return; }
    if (password.length < 8 && signup) { setError('Choose a password with at least 8 characters.'); return; }
    if (!password) { setError('Enter your password.'); return; }
    if (!supabase) { setError('Supabase is not configured. Use demo mode or add the public configuration.'); return; }
    setBusy(true);
    try {
      const result = signup ? await supabase.auth.signUp({ email: email.trim(), password }) : await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (result.error) {
        const code = result.error.code;
        throw new Error(code === 'invalid_credentials' ? 'Email or password is incorrect. Please try again.' : code === 'email_not_confirmed' ? 'Confirm your email first, then sign in here.' : result.error.status === 429 ? 'Too many attempts. Wait a moment before retrying.' : 'Unable to sign in or create your account. Check your connection and details, then retry.');
      }
      setPassword('');
      if (signup && !result.data.session) { setMessage('Check your inbox to confirm your email, then return here to sign in.'); setSignup(false); }
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'Connection failed. Please retry.'); }
    finally { setBusy(false); }
  }
  if (welcome && !restoreError) return <WelcomeScreen onContinue={() => setWelcome(false)} />;
  return <SafeAreaView style={s.screen} edges={['top', 'bottom']}>
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Pressable accessibilityRole="button" accessibilityLabel="Back to welcome" onPress={() => setWelcome(true)} style={{ minHeight: 44, justifyContent: 'center' }}><Ionicons name="chevron-back" size={24} color={theme.colors.text} /></Pressable>
        <Brand />
        <View style={styles.formHeader}><Text style={styles.formTitle}>{signup ? 'Find your next déclic.' : 'Welcome back.'}</Text><Text style={s.subtitle}>{signup ? 'Create an account to keep your learning with you.' : 'Sign in and pick up where you left off.'}</Text></View>
        <View style={{ flexDirection: 'row', gap: 24, borderBottomWidth: 1, borderBottomColor: theme.colors.border }}>{['Sign in', 'Create account'].map((label, i) => <Pressable key={label} accessibilityRole="tab" accessibilityState={{ selected: signup === Boolean(i) }} disabled={busy} onPress={() => { setSignup(Boolean(i)); setError(null); setPassword(''); }} style={{ paddingVertical: 16, borderBottomWidth: 2, borderBottomColor: signup === Boolean(i) ? theme.colors.accent : 'transparent' }}><Text style={{ color: signup === Boolean(i) ? theme.colors.text : theme.colors.muted, fontFamily: theme.fonts.bold }}>{label}</Text></Pressable>)}</View>
        {!authConfigured && <Text style={styles.notice}>Account setup is not configured on this device. The demo is available below.</Text>}
        <Text style={styles.label}>EMAIL ADDRESS</Text>
        <TextInput accessibilityLabel="Email address" testID="email-input" style={s.input} value={email} onChangeText={setEmail} placeholder="you@university.edu" placeholderTextColor="#788377" keyboardType="email-address" autoCapitalize="none" autoCorrect={false} autoComplete="email" textContentType="emailAddress" editable={!busy} returnKeyType="next" onSubmitEditing={() => passwordRef.current?.focus()} />
        <Text style={styles.label}>PASSWORD</Text>
        <TextInput ref={passwordRef} accessibilityLabel="Password" testID="password-input" style={s.input} value={password} onChangeText={setPassword} placeholder={signup ? 'At least 8 characters' : 'Your password'} placeholderTextColor="#788377" secureTextEntry={!showPassword} autoCapitalize="none" autoCorrect={false} textContentType={signup ? 'newPassword' : 'password'} editable={!busy} onSubmitEditing={() => void submit()} />
        <Pressable accessibilityRole="button" accessibilityLabel={showPassword ? 'Hide password' : 'Show password'} onPress={() => setShowPassword(value => !value)} style={{ minHeight: 44, justifyContent: 'center', alignSelf: 'flex-end' }}><Text style={styles.link}>{showPassword ? 'Hide password' : 'Show password'}</Text></Pressable>
        {(error || restoreError) && <Text accessibilityRole="alert" style={styles.error}>{error || restoreError}</Text>}
        {restoreError && <Pressable onPress={retryRestore}><Text style={styles.link}>Retry saved session</Text></Pressable>}
        {restoreError && <Pressable accessibilityRole="button" onPress={() => void resetSavedSession()}><Text style={styles.link}>Clear saved session and sign in</Text></Pressable>}
        {message && <Text accessibilityRole="alert" style={styles.notice}>{message}</Text>}
        <View style={{ marginTop: 22 }}><Button title={signup ? 'Create account' : 'Sign in'} busy={busy} disabled={!authConfigured} onPress={() => void submit()} testID="auth-submit" /></View>

        {config.previewEnabled && <><View style={styles.divider}><View style={styles.line} /><Text style={styles.dividerLabel}>JUST EXPLORING?</Text><View style={styles.line} /></View><Button title="Explore the demo" secondary onPress={enterPreview} testID="explore-demo" /><Text style={styles.demoNote}>Sample clips and course previews. No account needed.</Text></>}
      </ScrollView>
    </KeyboardAvoidingView>
  </SafeAreaView>;
}
const styles = StyleSheet.create({
  content: { padding: 24, paddingTop: 16, paddingBottom: 36, maxWidth: 520, width: '100%', alignSelf: 'center' },
  formHeader: { gap: 7, marginTop: 28, marginBottom: 12 }, formTitle: { color: theme.colors.text, fontFamily: theme.fonts.display, fontSize: 34, letterSpacing: -0.6 }, label: { color: theme.colors.muted, fontSize: 12, fontFamily: theme.fonts.bold, letterSpacing: 1.4, marginTop: 18, marginBottom: 9 },
  error: { fontFamily: theme.fonts.body, color: theme.colors.danger, fontSize: 13, lineHeight: 19, marginTop: 14 }, notice: { fontFamily: theme.fonts.body, color: theme.colors.accent, fontSize: 13, lineHeight: 19, marginTop: 14 }, link: { color: theme.colors.accent, fontFamily: theme.fonts.bold }, switch: { alignItems: 'center', paddingVertical: 21 },
  divider: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 18 }, line: { height: 1, backgroundColor: theme.colors.border, flex: 1 }, dividerLabel: { fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 9, letterSpacing: 1.5 }, demoNote: { fontFamily: theme.fonts.body, color: '#788377', textAlign: 'center', fontSize: 11, marginTop: 12 },
});
