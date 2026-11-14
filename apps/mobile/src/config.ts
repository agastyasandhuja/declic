export const config = {
  supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL ?? '',
  supabasePublishableKey: process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? '',
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? '',
  feedSource: process.env.EXPO_PUBLIC_FEED_SOURCE === 'api' ? 'api' as const : 'fixture' as const,
  previewEnabled: __DEV__ && process.env.EXPO_PUBLIC_ENABLE_PREVIEW !== 'false',
};
export const authConfigured = /^https:\/\//.test(config.supabaseUrl) && !config.supabaseUrl.includes('your-project') && config.supabasePublishableKey.startsWith('sb_publishable_') && !config.supabasePublishableKey.includes('replace_me');
