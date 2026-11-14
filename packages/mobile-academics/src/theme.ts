// Theme tokens for the academics UI (owner: Amogh).
//
// Adi owns the app-wide theme. These components accept a `theme` prop; this is
// the shape they need plus a neutral default so the package renders standalone
// (e.g. in isolation or a story) until Adi injects the real theme.

export interface AcademicsTheme {
  colors: {
    background: string;
    surface: string;
    text: string;
    textMuted: string;
    border: string;
    accent: string;
    ok: string;
    warn: string;
    bad: string;
    muted: string;
  };
  spacing: (n: number) => number;
  radius: number;
}

export const defaultTheme: AcademicsTheme = {
  colors: {
    background: '#0b0b0f',
    surface: '#17171f',
    text: '#f4f4f6',
    textMuted: '#a0a0ad',
    border: '#2a2a35',
    accent: '#6c8cff',
    ok: '#4cc29a',
    warn: '#e0b341',
    bad: '#e0685f',
    muted: '#6b6b78',
  },
  spacing: (n: number) => n * 8,
  radius: 14,
};

export function toneColor(theme: AcademicsTheme, tone: 'ok' | 'warn' | 'bad' | 'muted'): string {
  return theme.colors[tone];
}
