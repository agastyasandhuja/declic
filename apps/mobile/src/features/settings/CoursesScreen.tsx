import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { sharedStyles as s, theme } from '../../theme';

const courses = [
  { icon: 'git-network-outline' as const, code: 'COMPUTER SCIENCE', title: 'Data structures', detail: 'One pointer at a time.', topics: 'Linked lists · Trees · Graphs', accent: '#D5F985' },
  { icon: 'dice-outline' as const, code: 'MATHEMATICS', title: 'Probability', detail: 'Make sense of the unexpected.', topics: 'Distributions · Bayes · Expectation', accent: '#D6C3FF' },
  { icon: 'calculator-outline' as const, code: 'BUSINESS', title: 'Accounting', detail: 'See the story behind the numbers.', topics: 'Statements · Journals · Cash flow', accent: '#FFCDA1' },
];
export function CoursesScreen() {
  return <SafeAreaView style={s.screen} edges={['top']}><ScrollView contentContainerStyle={styles.content}>
    <Text style={s.eyebrow}>YOUR NEXT CHAPTER</Text><Text style={s.title}>A little closer{'\n'}to understanding.</Text><Text style={s.subtitle}>Your courses will become bite-sized ideas, right in your feed.</Text>
    <LinearGradient colors={['#34482B', '#1D2C1B']} style={styles.banner}><Ionicons name="leaf-outline" size={27} color={theme.colors.accent} /><View style={{ flex: 1, gap: 6 }}><Text style={styles.bannerTitle}>Learning is taking shape.</Text><Text style={styles.detail}>Canvas connection and course review will live here. For now, explore a sample semester.</Text></View></LinearGradient>
    <View style={styles.row}><Text style={styles.section}>A sample semester</Text><Text style={styles.badge}>SYNTHETIC PREVIEW</Text></View>
    {courses.map((course, index) => <View key={course.title} style={s.card}><View style={styles.courseHeader}><View style={[styles.courseIcon, { backgroundColor: course.accent + '18' }]}><Ionicons name={course.icon} size={24} color={course.accent} /></View><Text style={styles.number}>0{index + 1}</Text></View><Text style={[styles.code, { color: course.accent }]}>{course.code}</Text><Text style={styles.courseTitle}>{course.title}</Text><Text style={s.subtitle}>{course.detail}</Text><View style={styles.rule} /><Text style={styles.topics}>{course.topics}</Text></View>)}
    <Text style={styles.footer}>These cards are sample data, not imported Canvas courses.</Text>
  </ScrollView></SafeAreaView>;
}
const styles = StyleSheet.create({
  content: { padding: 24, paddingTop: 24, gap: 18, paddingBottom: 36, maxWidth: 640, width: '100%', alignSelf: 'center' }, banner: { padding: 22, borderRadius: 23, flexDirection: 'row', gap: 16, marginVertical: 9 }, bannerTitle: { color: theme.colors.text, fontSize: 16, fontWeight: '600' }, detail: { color: '#B5C6AB', lineHeight: 20, fontSize: 12 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, section: { color: theme.colors.text, fontSize: 17, fontWeight: '600' }, badge: { color: theme.colors.muted, fontSize: 8, fontWeight: '700', letterSpacing: 1 }, courseHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 23 },
  courseIcon: { padding: 12, borderRadius: 15 }, number: { color: '#5B6656', fontSize: 32, fontWeight: '300' }, code: { fontSize: 9, letterSpacing: 1.8, fontWeight: '700', marginBottom: 9 }, courseTitle: { color: theme.colors.text, fontSize: 25, letterSpacing: -0.6, fontWeight: '600', marginBottom: 7 }, rule: { height: 1, backgroundColor: theme.colors.border, marginVertical: 18 }, topics: { color: '#ABB8A4', fontSize: 11 }, footer: { color: '#7D8876', fontSize: 11, lineHeight: 17 },
});
