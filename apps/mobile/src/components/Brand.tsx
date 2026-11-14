import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { theme } from '../theme';
export function Brand({ size = 28, icon = false }: { size?: number; icon?: boolean }) {
  return <View accessibilityLabel="déclic" style={styles.row}>
    {icon && <View style={styles.tile}><Text style={styles.d}>d</Text><View style={styles.tick} /></View>}
    <View style={{ flexDirection: 'row', alignItems: 'baseline' }}><Text style={[styles.word, { fontSize: size }]}>d</Text><View><Text style={[styles.word, { fontSize: size }]}>e</Text><View style={{ position: 'absolute', top: size * .12, left: size * .2, width: size * .3, height: size * .12, borderRadius: 4, backgroundColor: theme.colors.coral, transform: [{ rotate: '-28deg' }] }} /></View><Text style={[styles.word, { fontSize: size }]}>clic</Text></View>
  </View>;
}
const styles = StyleSheet.create({ row: { flexDirection: 'row', alignItems: 'center', gap: 10 }, word: { fontFamily: 'Syne', fontWeight: '800', color: theme.colors.text, letterSpacing: -1.4 }, tile: { width: 40, height: 40, borderRadius: 12, backgroundColor: theme.colors.accent, alignItems: 'center', justifyContent: 'center' }, d: { fontFamily: 'Syne', fontSize: 31, fontWeight: '800', color: theme.colors.background, marginTop: -5 }, tick: { position: 'absolute', right: 7, top: 7, width: 10, height: 4, borderRadius: 2, backgroundColor: theme.colors.coral, transform: [{ rotate: '-28deg' }] } });
