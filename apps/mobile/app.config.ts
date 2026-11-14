import type { ConfigContext, ExpoConfig } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: config.name ?? 'Study in your feed',
  slug: config.slug ?? 'hackumass-14',
  extra: { ...config.extra, privatePreviewApi: process.env.HACKUMASS_PREVIEW_API === '1' },
});
