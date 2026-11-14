import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Brand } from '../../components/Brand';
import { theme } from '../../theme';

export function FeedHeader({ top, muted, onMute, fill, onFill }: {
  top: number; muted?: boolean; onMute?(): void; fill?: boolean; onFill?(): void;
}) {
  return (
    <View pointerEvents="box-none" style={[styles.header, { top }]}>
      <Brand size={34} />
      <View pointerEvents="box-none" style={styles.headerActions}>
        {onFill && <FeedIconButton round label={fill ? 'Fit whole video' : 'Fill screen'} icon={fill ? 'contract-outline' : 'expand-outline'} onPress={onFill} />}
        {onMute && <FeedIconButton round label={muted ? 'Unmute video' : 'Mute video'} icon={muted ? 'volume-mute-outline' : 'volume-high-outline'} onPress={onMute} />}
      </View>
    </View>
  );
}

export function FeedIconButton({ label, icon, onPress, selected, color = theme.colors.text, round = false, disabled = false, testID }: {
  label: string; icon: keyof typeof Ionicons.glyphMap; onPress(): void;
  selected?: boolean; color?: string; round?: boolean; disabled?: boolean; testID?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected, disabled }}
      disabled={disabled}
      testID={testID}
      onPress={onPress}
      style={({ pressed }) => [styles.action, round && styles.round, (pressed || disabled) && styles.dimmed]}
    >
      <Ionicons name={icon} size={round ? 20 : 26} color={color} style={!round && styles.iconShadow} />
    </Pressable>
  );
}

export function FeedScrim() {
  return <LinearGradient pointerEvents="none" colors={['#00000088', '#00000000', '#00000000', '#000000D9']} locations={[0, 0.20, 0.63, 1]} style={StyleSheet.absoluteFill} />;
}

export function FeedCaption({ byline, title, caption, children }: {
  byline?: string | null; title?: string; caption?: string;
  children?: React.ReactNode;
}) {
  return (
    <View pointerEvents="box-none" style={styles.description}>
      {!!byline && <Text numberOfLines={1} style={styles.byline}>{byline}</Text>}
      {!!title && <Text numberOfLines={2} style={styles.title}>{title}</Text>}
      {!!caption && <Text numberOfLines={3} maxFontSizeMultiplier={1.4} style={styles.caption}>{caption}</Text>}
      {children}
    </View>
  );
}

export const feedRail = { position: 'absolute', right: 10, bottom: 20, gap: 6 } as const;

const styles = StyleSheet.create({
  header: { position: 'absolute', left: 16, right: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, minHeight: 44 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  action: { width: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  round: { borderRadius: 22, backgroundColor: '#09090B55', borderWidth: 1, borderColor: '#FFFFFF35' },
  dimmed: { opacity: 0.65 },
  iconShadow: { textShadowColor: '#000000B3', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 5 },
  description: { position: 'absolute', left: 16, right: 70, bottom: 22, gap: 7 },
  byline: { fontFamily: theme.fonts.bold, fontSize: 15, lineHeight: 20, color: theme.colors.text, textShadowColor: '#000000B3', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 4 },
  title: { fontFamily: theme.fonts.bold, fontSize: 17, lineHeight: 22, color: theme.colors.text },
  caption: { fontFamily: theme.fonts.body, fontSize: 14, lineHeight: 20, color: theme.colors.text, textShadowColor: '#000000B3', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 4 },
});
