import React, { useRef } from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Brand } from '../../components/Brand';
import { theme } from '../../theme';

export function FeedHeader({ top }: { top: number }) {
  return <View pointerEvents="none" style={[styles.header, { top }]}><Brand size={30} /></View>;
}

export function FeedIconButton({ label, icon, onPress, selected, color = theme.colors.text, round = false, disabled = false, testID, reducedMotion = false }: {
  label: string; icon: keyof typeof Ionicons.glyphMap; onPress(): void;
  selected?: boolean; color?: string; round?: boolean; disabled?: boolean; testID?: string; reducedMotion?: boolean;
}) {
  const scale = useRef(new Animated.Value(1)).current;
  const press = () => {
    if (!reducedMotion) {
      scale.setValue(0.8);
      Animated.spring(scale, { toValue: 1, friction: 3, tension: 180, useNativeDriver: true }).start();
    }
    onPress();
  };
  return (
    <Animated.View style={{ transform: [{ scale }] }}><Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected, disabled }}
      disabled={disabled}
      testID={testID}
      onPress={press}
      style={({ pressed }) => [styles.action, round && styles.round, (pressed || disabled) && styles.dimmed]}
    >
      <Ionicons name={icon} size={round ? 20 : 26} color={color} style={!round && styles.iconShadow} />
    </Pressable></Animated.View>
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

export const feedRail = { position: 'absolute', right: 10, bottom: 46, gap: 12 } as const;

const styles = StyleSheet.create({
  header: { position: 'absolute', left: 16, right: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, minHeight: 44 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  action: { width: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  round: { borderRadius: 22, backgroundColor: '#09090B55', borderWidth: 1, borderColor: '#FFFFFF35' },
  dimmed: { opacity: 0.65 },
  iconShadow: { textShadowColor: '#000000B3', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 5 },
  description: { position: 'absolute', left: 16, right: 70, bottom: 42, gap: 7 },
  byline: { fontFamily: theme.fonts.bold, fontSize: 15, lineHeight: 20, color: theme.colors.text, textShadowColor: '#000000B3', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 4 },
  title: { fontFamily: theme.fonts.bold, fontSize: 17, lineHeight: 22, color: theme.colors.text },
  caption: { fontFamily: theme.fonts.body, fontSize: 14, lineHeight: 20, color: theme.colors.text, textShadowColor: '#000000B3', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 4 },
});
