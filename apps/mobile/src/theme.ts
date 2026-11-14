import { StyleSheet } from 'react-native';

export const theme = {
  colors: { background: '#101211', surface: '#1D211E', elevated: '#292E29', text: '#F5F4E9', muted: '#A5B0A5', accent: '#D5F985', ink: '#16210B', border: '#343C33', danger: '#FFB6A9' },
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 },
  radius: { sm: 12, md: 20, lg: 28 },
} as const;
export const sharedStyles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.colors.background },
  title: { color: theme.colors.text, fontSize: 34, lineHeight: 39, fontWeight: '700', letterSpacing: -1.2 },
  subtitle: { color: theme.colors.muted, fontSize: 15, lineHeight: 22 },
  eyebrow: { color: theme.colors.accent, fontSize: 11, fontWeight: '800', letterSpacing: 2 },
  card: { backgroundColor: theme.colors.surface, borderRadius: 22, padding: 22, borderWidth: 1, borderColor: theme.colors.border },
  input: { backgroundColor: theme.colors.surface, color: theme.colors.text, borderWidth: 1, borderColor: theme.colors.border, borderRadius: 16, paddingHorizontal: 17, paddingVertical: 17, fontSize: 16 },
});
