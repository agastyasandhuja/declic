import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';
import { theme } from '../theme';

export function Button({ title, onPress, busy = false, secondary = false, disabled = false, testID }: {
  title: string; onPress(): void; busy?: boolean; secondary?: boolean; disabled?: boolean; testID?: string;
}) {
  return <Pressable accessibilityRole="button" accessibilityLabel={title} disabled={busy || disabled} onPress={onPress} testID={testID}
    style={({ pressed }) => [styles.button, secondary && styles.secondary, { opacity: pressed || disabled || busy ? 0.65 : 1 }]}>
    {busy && <ActivityIndicator color={secondary ? theme.colors.text : theme.colors.ink} />}<Text style={[styles.label, secondary && { color: theme.colors.text }]}>{busy ? `${title}…` : title}</Text>
  </Pressable>;
}
const styles = StyleSheet.create({
  button: { minHeight: 54, paddingHorizontal: 20, paddingVertical: 16, borderRadius: 999, backgroundColor: theme.colors.text, flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center' },
  secondary: { backgroundColor: theme.colors.elevated, borderWidth: 1, borderColor: theme.colors.border },
  label: { color: theme.colors.ink, fontFamily: theme.fonts.bold, fontSize: 16 },
});
