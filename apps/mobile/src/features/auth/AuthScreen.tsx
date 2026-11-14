import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { supabase } from '../../lib/auth/supabase';
import { authConfigured, config } from '../../config';
import { useAuth } from '../../state/AuthProvider';
import { Button } from '../../components/Button';
import { sharedStyles as s, theme } from '../../theme';

export function AuthScreen() {
  const { enterPreview, error: restoreError, retryRestore } = useAuth();
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState<string | null>(null); const [error, setError] = useState<string | null>(null);
  async function submit() {
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
  return <SafeAreaView style={s.screen} edges={['top', 'bottom']}>
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.wordmark}><View style={styles.logo}><Ionicons name="play" size={18} color={theme.colors.ink} /></View><Text style={styles.brand}>study / scroll</Text><Text style={styles.edition}>HACKUMASS XIV</Text></View>
        <LinearGradient colors={['#35472C', '#1B241A', '#111511']} style={styles.hero}>
          <View style={styles.heroTop}><Text style={s.eyebrow}>A LITTLE SCROLL. A LITTLE SMARTER.</Text><Ionicons name="sparkles-outline" size={24} color={theme.colors.accent} /></View>
          <Text style={styles.heroTitle}>Your next break.{ '\n' }Your next{ '\n' }breakthrough.</Text>
          <View style={styles.heroFoot}><View style={styles.dot} /><Text style={styles.heroNote}>Good videos. Ideas that stay with you.</Text></View>
          <View style={styles.orbit} />
        </LinearGradient>
        <View style={styles.formHeader}><Text style={styles.formTitle}>{signup ? 'Make room for curiosity.' : 'Welcome to your next chapter.'}</Text><Text style={s.subtitle}>{signup ? 'Create an account to keep your learning with you.' : 'Sign in and pick up where you left off.'}</Text></View>
        {!authConfigured && <Text style={styles.notice}>Account setup is not configured on this device. The demo is available below.</Text>}
        <Text style={styles.label}>EMAIL ADDRESS</Text>
        <TextInput accessibilityLabel="Email address" testID="email-input" style={s.input} value={email} onChangeText={setEmail} placeholder="you@university.edu" placeholderTextColor="#788377" keyboardType="email-address" autoCapitalize="none" autoCorrect={false} autoComplete="email" textContentType="emailAddress" editable={!busy} />
        <Text style={styles.label}>PASSWORD</Text>
        <TextInput accessibilityLabel="Password" testID="password-input" style={s.input} value={password} onChangeText={setPassword} placeholder={signup ? 'At least 8 characters' : 'Your password'} placeholderTextColor="#788377" secureTextEntry autoCapitalize="none" autoCorrect={false} textContentType={signup ? 'newPassword' : 'password'} editable={!busy} onSubmitEditing={() => void submit()} />
        {(error || restoreError) && <Text accessibilityRole="alert" style={styles.error}>{error || restoreError}</Text>}
        {restoreError && <Pressable onPress={retryRestore}><Text style={styles.link}>Retry saved session</Text></Pressable>}
        {message && <Text accessibilityRole="alert" style={styles.notice}>{message}</Text>}
        <View style={{ marginTop: 22 }}><Button title={signup ? 'Create account' : 'Sign in'} busy={busy} disabled={!authConfigured} onPress={() => void submit()} testID="auth-submit" /></View>
        <Pressable accessibilityRole="button" disabled={busy} onPress={() => { setSignup(!signup); setError(null); setMessage(null); setPassword(''); }} style={styles.switch}><Text style={s.subtitle}>{signup ? 'Already have an account? ' : 'New here? '}<Text style={styles.link}>{signup ? 'Sign in' : 'Create an account'}</Text></Text></Pressable>
        {config.previewEnabled && <><View style={styles.divider}><View style={styles.line} /><Text style={styles.dividerLabel}>JUST EXPLORING?</Text><View style={styles.line} /></View><Button title="Explore the demo" secondary onPress={enterPreview} testID="explore-demo" /><Text style={styles.demoNote}>Sample clips and course previews. Nothing to connect yet.</Text></>}
      </ScrollView>
    </KeyboardAvoidingView>
  </SafeAreaView>;
}
const styles = StyleSheet.create({
  content: { padding: 24, paddingTop: 16, paddingBottom: 36, maxWidth: 520, width: '100%', alignSelf: 'center' },
  wordmark: { flexDirection: 'row', alignItems: 'center', gap: 9, marginBottom: 26 }, logo: { width: 32, height: 32, borderRadius: 11, alignItems: 'center', justifyContent: 'center', backgroundColor: theme.colors.accent },
  brand: { color: theme.colors.text, fontWeight: '700', fontSize: 20, letterSpacing: -0.6 }, edition: { color: theme.colors.muted, fontSize: 9, letterSpacing: 1.2, marginLeft: 'auto' },
  hero: { padding: 24, paddingBottom: 26, borderRadius: 26, minHeight: 272, overflow: 'hidden', borderWidth: 1, borderColor: '#40513A' }, heroTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  heroTitle: { fontSize: 40, lineHeight: 43, letterSpacing: -1.5, fontWeight: '700', color: theme.colors.text, marginTop: 24, zIndex: 1 },
  heroFoot: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 26, zIndex: 1 }, heroNote: { color: '#BECDB6', fontSize: 11 }, dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: theme.colors.accent },
  orbit: { position: 'absolute', right: -100, bottom: -130, width: 290, height: 290, borderRadius: 145, borderWidth: 42, borderColor: '#C4EA6520', transform: [{ rotate: '35deg' }] },
  formHeader: { gap: 7, marginTop: 28, marginBottom: 12 }, formTitle: { color: theme.colors.text, fontSize: 22, fontWeight: '600', letterSpacing: -0.6 }, label: { color: theme.colors.muted, fontSize: 10, fontWeight: '700', letterSpacing: 1.4, marginTop: 18, marginBottom: 9 },
  error: { color: theme.colors.danger, fontSize: 13, lineHeight: 19, marginTop: 14 }, notice: { color: theme.colors.accent, fontSize: 13, lineHeight: 19, marginTop: 14 }, link: { color: theme.colors.accent, fontWeight: '600' }, switch: { alignItems: 'center', paddingVertical: 21 },
  divider: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 18 }, line: { height: 1, backgroundColor: theme.colors.border, flex: 1 }, dividerLabel: { color: theme.colors.muted, fontSize: 9, letterSpacing: 1.5 }, demoNote: { color: '#788377', textAlign: 'center', fontSize: 11, marginTop: 12 },
});
