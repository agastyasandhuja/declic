// Small status pill (owner: Amogh).
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { AcademicsTheme } from '../theme';
import { toneColor } from '../theme';
import type { Tone } from '../viewmodel/format';

export function StatusBadge({ label, tone, theme }: { label: string; tone: Tone; theme: AcademicsTheme }) {
  const color = toneColor(theme, tone);
  return (
    <View style={[styles.pill, { borderColor: color, backgroundColor: color + '22' }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3, alignSelf: 'flex-start' },
  text: { fontSize: 12, fontWeight: '600' },
});
