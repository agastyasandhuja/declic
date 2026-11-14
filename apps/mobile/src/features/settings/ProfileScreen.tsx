import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../components/Button';
import { useAuth } from '../../state/AuthProvider';
import { sharedStyles as s, theme } from '../../theme';
import type { EntertainmentVideo } from '../../contracts/generated';

export interface PlaybackPreferences { muted: boolean; captions: boolean; reducedMotion: boolean }

export function ProfileScreen({ clicked, saved, onOpen, preferences, setPreferences, openCourses, openLab }: {
  clicked: EntertainmentVideo[];
  saved: EntertainmentVideo[];
  onOpen(video: EntertainmentVideo): void;
  preferences: PlaybackPreferences;
  setPreferences(value: PlaybackPreferences): void;
  openCourses(): void;
  openLab(): void;
}) {
  const { user, mode, signOut } = useAuth();
  const [collection, setCollection] = useState<'clicked' | 'saved'>('clicked');
  const [error, setError] = useState<string | null>(null);
  const name = mode === 'preview' ? 'Curious human' : user?.display_name || user?.email?.split('@')[0] || 'Your profile';
  const items = collection === 'clicked' ? clicked : saved;

  return (
    <SafeAreaView style={s.screen} edges={['top']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text accessibilityRole="header" style={s.title}>You</Text>
        <View style={styles.identity}>
          <LinearGradient colors={[theme.colors.accent, theme.colors.coral]} style={styles.avatar}>
            <Text style={styles.initials}>{Array.from(name).slice(0, 2).join('').toUpperCase()}</Text>
          </LinearGradient>
          <View style={styles.grow}>
            <Text style={styles.name}>{name}</Text>
            <Text style={styles.muted}>{mode === 'preview' ? 'Demo explorer' : user?.email}</Text>
          </View>
        </View>

        <View accessibilityRole="tablist" style={styles.segment}>
          {([{ key: 'clicked', label: 'Clicked', count: clicked.length, icon: 'heart' }, { key: 'saved', label: 'Saved', count: saved.length, icon: 'bookmark' }] as const).map(tab => (
            <Pressable key={tab.key} accessibilityRole="tab" accessibilityState={{ selected: collection === tab.key }} onPress={() => setCollection(tab.key)} style={[styles.pill, collection === tab.key && styles.activePill]}>
              <Ionicons name={tab.icon} color={collection === tab.key ? theme.colors.accent : theme.colors.muted} size={16} />
              <Text style={styles.label}>{tab.label}</Text>
              <Text style={styles.muted}>{tab.count}</Text>
            </Pressable>
          ))}
        </View>
        {items.length ? (
          <View style={styles.grid}>{items.map(video => (
            <Pressable key={video.video_id} accessibilityRole="button" accessibilityLabel={video.caption ? `Play ${video.caption}` : 'Play video'} onPress={() => onOpen(video)} style={styles.video}>
              <Ionicons name="play-circle" size={30} color={theme.colors.accent} />
              <Text numberOfLines={3} style={styles.label}>{video.caption || video.creator.display_name || video.creator.handle}</Text>
            </Pressable>
          ))}</View>
        ) : (
          <View style={styles.empty}>
            <Ionicons name={collection === 'clicked' ? 'heart-outline' : 'bookmark-outline'} size={24} color={theme.colors.muted} />
            <Text style={styles.emptyText}>{collection === 'clicked' ? 'Tap a heart to collect a clip here.' : 'Tap a bookmark to come back to a clip.'}</Text>
          </View>
        )}
        <Text style={styles.muted}>Collections are kept for this session.</Text>

        <Text accessibilityRole="header" style={styles.heading}>Connections</Text>
        <View style={styles.card}>
          <Pressable accessibilityRole="button" onPress={openCourses} style={styles.row}>
            <View style={[styles.provider, { backgroundColor: '#E5412E' }]}><Ionicons name="school-outline" color="white" size={23} /></View>
            <View style={styles.grow}><Text style={styles.label}>Canvas</Text><Text style={styles.muted}>Manage in Courses</Text></View>
            <Ionicons name="chevron-forward" color={theme.colors.muted} size={20} />
          </Pressable>
          {mode !== 'preview' && (
            <Pressable accessibilityRole="button" onPress={openCourses} style={[styles.row, styles.divider]}>
              <LinearGradient colors={['#F9CE34', '#EE2A7B', '#6228D7']} style={styles.provider}><Ionicons name="logo-instagram" color="white" size={24} /></LinearGradient>
              <View style={styles.grow}><Text style={styles.label}>Instagram</Text><Text style={styles.muted}>Manage in Courses</Text></View>
              <Ionicons name="chevron-forward" color={theme.colors.muted} size={20} />
            </Pressable>
          )}
        </View>

        <Text accessibilityRole="header" style={styles.heading}>Playback</Text>
        <View style={styles.card}>
          {([{ key: 'muted', label: 'Mute videos', sub: 'Start and continue without sound' }, { key: 'captions', label: 'Show descriptions', sub: 'Show clip descriptions over videos' }, { key: 'reducedMotion', label: 'Reduce motion', sub: 'Switch clips without animation' }] as const).map((pref, index) => (
            <View key={pref.key} style={[styles.row, index > 0 && styles.divider]}>
              <View style={styles.grow}><Text style={styles.label}>{pref.label}</Text><Text style={styles.muted}>{pref.sub}</Text></View>
              <Switch accessibilityLabel={pref.label} value={preferences[pref.key]} onValueChange={value => setPreferences({ ...preferences, [pref.key]: value })} trackColor={{ true: theme.colors.accent, false: theme.colors.border }} />
            </View>
          ))}
        </View>
        {error && <Text accessibilityRole="alert" style={[styles.muted, { color: theme.colors.danger }]}>{error}</Text>}
        <Button title={mode === 'preview' ? 'Leave demo' : 'Sign out'} secondary onPress={() => { void signOut().catch(() => setError('Sign-out failed. Please retry.')); }} />
        {__DEV__ && <Button title="Developer lab" secondary onPress={openLab} testID="open-lab" />}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 20, gap: 14, paddingBottom: 30, maxWidth: 560, width: '100%', alignSelf: 'center' },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 8 },
  avatar: { width: 66, height: 66, borderRadius: 33, alignItems: 'center', justifyContent: 'center' },
  initials: { fontFamily: theme.fonts.display, fontSize: 24, color: theme.colors.ink },
  name: { fontFamily: theme.fonts.display, fontSize: 23, lineHeight: 26, color: theme.colors.text, letterSpacing: -0.5 },
  heading: { fontFamily: theme.fonts.display, fontSize: 21, lineHeight: 26, color: theme.colors.text, marginTop: 8 },
  muted: { fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 12, lineHeight: 18 },
  segment: { flexDirection: 'row', padding: 4, borderRadius: 999, backgroundColor: theme.colors.surface, gap: 4 },
  pill: { flex: 1, minHeight: 44, paddingHorizontal: 8, borderRadius: 999, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  activePill: { backgroundColor: theme.colors.elevated },
  label: { fontFamily: theme.fonts.bold, color: theme.colors.text, fontSize: 15 },
  empty: { backgroundColor: theme.colors.surface, borderWidth: 1, borderColor: theme.colors.border, padding: 16, borderRadius: 20, gap: 12, flexDirection: 'row', alignItems: 'center' },
  emptyText: { flex: 1, fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 14, lineHeight: 20 },
  card: { backgroundColor: theme.colors.surface, borderWidth: 1, borderColor: theme.colors.border, borderRadius: 22, overflow: 'hidden' },
  row: { flexDirection: 'row', gap: 12, padding: 14, alignItems: 'center', minHeight: 68 },
  divider: { borderTopWidth: 1, borderTopColor: theme.colors.elevated },
  grow: { flex: 1, gap: 4 },
  provider: { width: 40, height: 40, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  video: { width: '31%', minHeight: 124, backgroundColor: theme.colors.elevated, borderRadius: 14, padding: 12, justifyContent: 'space-between', gap: 8 },
});
