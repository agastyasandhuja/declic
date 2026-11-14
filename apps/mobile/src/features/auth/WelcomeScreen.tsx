import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Brand } from '../../components/Brand';
import { Button } from '../../components/Button';
import { theme } from '../../theme';
import { config } from '../../config';
import { useAuth } from '../../state/AuthProvider';
export function WelcomeScreen({ onContinue }: { onContinue(): void }) {
  const { enterPreview } = useAuth();
  return <SafeAreaView style={styles.root}><ScrollView contentContainerStyle={styles.content}>
    <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={styles.mosaic}>
      {[['Fitness', 'barbell-outline', '#35232D'], ['A little curiosity', 'planet-outline', '#30264A'], ['Good food', 'restaurant-outline', '#453324'], ['One new idea', 'bulb-outline', '#40336A'], ['Outside again', 'leaf-outline', '#203A38'], ['Your next discovery', 'sparkles-outline', '#422D40']].map(([label, name, color], i) => <View key={label} style={[styles.tile, { backgroundColor: color, marginTop: i % 3 === 1 ? 24 : 0 }]}><Ionicons name={name as keyof typeof Ionicons.glyphMap} size={42} color={i === 3 ? theme.colors.accent : '#FFFFFF60'} /><Text style={styles.tileLabel}>{label}</Text>{i === 3 && <Text style={styles.study}>STUDY</Text>}</View>)}
      <LinearGradient colors={['#09090B00', '#09090B']} style={StyleSheet.absoluteFill} />
    </View>
    <View style={styles.bottom}><Brand icon /><Text style={styles.headline}>First you swipe.{'\n'}Then it <Text style={{ color: theme.colors.accent }}>clicks.</Text></Text><Text style={styles.sub}>Your favorite scroll. A little more discovery.</Text><Button title="Continue with email" onPress={onContinue} testID="continue-email" />{config.previewEnabled && <Button title="Explore the demo" secondary onPress={enterPreview} testID="explore-demo" />}</View>
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({ root: { flex: 1, backgroundColor: theme.colors.background }, content: { flexGrow: 1, maxWidth: 520, width: '100%', alignSelf: 'center', paddingBottom: 28 }, mosaic: { height: 310, flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginHorizontal: -20, transform: [{ rotate: '-6deg' }], overflow: 'hidden' }, tile: { width: '30%', height: 170, borderRadius: 18, padding: 14, justifyContent: 'center', alignItems: 'center', gap: 20 }, tileLabel: { color: '#FFFFFFA0', fontSize: 11 }, study: { position: 'absolute', top: 12, left: 12, fontSize: 10, fontWeight: '800', color: theme.colors.ink, backgroundColor: theme.colors.accent, padding: 5, borderRadius: 5 }, bottom: { paddingHorizontal: 24, gap: 14, marginTop: -22 }, headline: { fontFamily: 'Syne', fontSize: 46, lineHeight: 47, fontWeight: '800', letterSpacing: -2, color: theme.colors.text, marginVertical: 12 }, sub: { color: theme.colors.muted, fontFamily: 'Jakarta', fontSize: 15, marginBottom: 8 } });
