import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Button } from '../../components/Button';
import { theme } from '../../theme';
import type { UnifiedQuiz } from './unified';

export interface QuizFeedback {
  correct: boolean;
  explanation: string;
}

export function FeedQuiz({ quiz, top, answer, feedback, busy, ready, answerSent, error, onSelect, onSubmit, onContinue, onRecover, onRetry }: {
  quiz: UnifiedQuiz['quiz'];
  top: number;
  answer: string | null;
  feedback: QuizFeedback | null;
  busy: boolean;
  ready: boolean;
  answerSent: boolean;
  error: string | null;
  onSelect(id: string): void;
  onSubmit(): void;
  onContinue(): void;
  onRecover(): void;
  onRetry(): void;
}) {
  const feedbackColor = feedback?.correct ? theme.colors.success : theme.colors.coral;

  return (
    <View style={styles.screen}>
      <LinearGradient pointerEvents="none" colors={['#9D86FF2E', '#09090B00']} start={{ x: 1, y: 0 }} end={{ x: 0.35, y: 1 }} style={styles.glow} />
      <ScrollView contentContainerStyle={[styles.content, { paddingTop: top }]}>
        <View style={styles.badge}><Text style={styles.badgeText}>QUICK CHECK</Text></View>
        <Text accessibilityRole="header" style={styles.prompt}>{quiz.prompt}</Text>
        <View accessibilityRole="radiogroup" style={styles.options}>
          {quiz.options.map((option, index) => {
            const selected = answer === option.option_id;
            const color = feedback ? feedbackColor : theme.colors.accent;
            const disabled = !!feedback || busy || answerSent;
            return (
              <Pressable
                key={option.option_id}
                accessibilityRole="radio"
                accessibilityState={{ checked: selected, disabled }}
                accessibilityLabel={option.text}
                disabled={disabled}
                onPress={() => onSelect(option.option_id)}
                style={[styles.option, selected && [styles.selected, { borderColor: color }]]}
              >
                <View style={[styles.letter, selected && { backgroundColor: color }]}>
                  <Text style={[styles.letterText, selected && styles.selectedLetter]}>{String.fromCharCode(65 + index)}</Text>
                </View>
                <Text style={styles.optionText}>{option.text}</Text>
                <Ionicons name={selected ? 'radio-button-on' : 'ellipse-outline'} size={22} color={selected ? color : theme.colors.muted} />
              </Pressable>
            );
          })}
        </View>
        {error && (
          <View style={styles.error}>
            <Text accessibilityRole="alert" style={styles.errorText}>{error}</Text>
            {ready && !feedback && <Button title="Continue without grading" secondary busy={busy} onPress={onRecover} />}
            {!ready && <Button title="Retry question" secondary onPress={onRetry} />}
          </View>
        )}
        {feedback ? (
          <>
            <View accessibilityLiveRegion="polite" style={styles.feedback}>
              <Ionicons name={feedback.correct ? 'checkmark-circle' : 'information-circle'} size={23} color={feedbackColor} />
              <View style={styles.feedbackCopy}>
                <Text style={[styles.letterText, { color: feedbackColor }]}>{feedback.correct ? 'Correct' : 'Not quite'}</Text>
                {!!feedback.explanation && <Text style={styles.body}>{feedback.explanation}</Text>}
              </View>
            </View>
            <Button title="Continue watching" onPress={onContinue} />
          </>
        ) : (
          <>
            <Button title={error && answerSent ? 'Retry answer' : ready ? 'Check answer' : 'Preparing question'} disabled={!ready || !answer} busy={busy} onPress={onSubmit} />
            <View style={styles.lock}>
              <Ionicons name="lock-closed" size={14} color={theme.colors.muted} />
              <Text style={styles.lockText}>Answer to keep scrolling</Text>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.colors.background },
  glow: { position: 'absolute', left: 0, right: 0, top: 0, height: 250 },
  content: { flexGrow: 1, width: '100%', maxWidth: 560, alignSelf: 'center', paddingHorizontal: 20, paddingBottom: 20, gap: 14 },
  badge: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5, backgroundColor: theme.colors.accent },
  badgeText: { fontFamily: theme.fonts.bold, fontSize: 12, color: theme.colors.ink },
  prompt: { fontFamily: theme.fonts.display, fontSize: 26, lineHeight: 30, letterSpacing: -0.7, color: theme.colors.text },
  options: { gap: 10, marginTop: 4 },
  option: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 58, backgroundColor: theme.colors.surface, borderWidth: 1.5, borderColor: theme.colors.elevated, borderRadius: 18, paddingHorizontal: 14, paddingVertical: 10 },
  selected: { backgroundColor: '#211B35' },
  letter: { width: 28, height: 28, alignItems: 'center', justifyContent: 'center', borderRadius: 14, backgroundColor: theme.colors.elevated },
  letterText: { fontFamily: theme.fonts.bold, fontSize: 13, color: theme.colors.text },
  selectedLetter: { color: theme.colors.ink },
  optionText: { flex: 1, fontFamily: theme.fonts.bold, fontSize: 15, lineHeight: 21, color: theme.colors.text },
  feedback: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, padding: 14, borderRadius: 18, backgroundColor: theme.colors.surface },
  feedbackCopy: { flex: 1, gap: 4 },
  body: { fontFamily: theme.fonts.body, fontSize: 15, lineHeight: 22, color: theme.colors.text },
  lock: { marginTop: 'auto', minHeight: 30, flexDirection: 'row', gap: 7, alignItems: 'center', justifyContent: 'center' },
  lockText: { fontFamily: theme.fonts.body, fontSize: 13, color: theme.colors.muted },
  error: { gap: 8 },
  errorText: { fontFamily: theme.fonts.body, fontSize: 14, lineHeight: 20, color: theme.colors.danger },
});
