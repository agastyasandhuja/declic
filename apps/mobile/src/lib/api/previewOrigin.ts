export function developmentPreviewOrigin(enabled: boolean, hostUri?: string): string {
  if (!enabled || !hostUri) return '';
  try {
    const url = new URL(`https://${hostUri}`);
    return url.hostname.endsWith('.on.expo.app') && !url.username && !url.password && url.pathname === '/' && !url.search && !url.hash ? url.origin : '';
  } catch { return ''; }
}
