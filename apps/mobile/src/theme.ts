import { StyleSheet } from 'react-native';

export const theme = {
  colors: { background: '#09090B', surface: '#16161B', elevated: '#22222A', text: '#F7F6FB', muted: '#A4A2B4', accent: '#9D86FF', ink: '#0B0716', border: '#2D2D36', danger: '#FF8A8A', coral: '#FF6B6B', success: '#5BD38C' },
  fonts: { display: 'Syne-ExtraBold', body: 'PlusJakartaSans-Regular', bold: 'PlusJakartaSans-Bold' },
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 },
  radius: { sm: 12, md: 20, lg: 28 },
} as const;

export const sharedStyles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.colors.background },
  title: { fontFamily: theme.fonts.display, color: theme.colors.text, fontSize: 34, lineHeight: 39, letterSpacing: -1.2 },
  subtitle: { fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 15, lineHeight: 22 },
  eyebrow: { fontFamily: theme.fonts.bold, color: theme.colors.accent, fontSize: 12, letterSpacing: 1.4 },
  card: { backgroundColor: theme.colors.surface, borderRadius: 22, padding: 22, borderWidth: 1, borderColor: theme.colors.border },
  input: { fontFamily: theme.fonts.body, backgroundColor: theme.colors.surface, color: theme.colors.text, borderWidth: 1, borderColor: theme.colors.border, borderRadius: 16, paddingHorizontal: 17, paddingVertical: 17, fontSize: 16 },
});
