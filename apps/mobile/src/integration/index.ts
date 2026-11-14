import type { ComponentType } from 'react';
import type { CurrentUser } from '../contracts/generated';
import type { ApiClient } from '../lib/api/client';
import type { theme } from '../theme';

export interface FeatureScreenProps {
  user: CurrentUser;
  api: ApiClient;
  theme: typeof theme;
  isPreview: boolean;
  onBack(): void;
  onOpenFeed(): void;
}
export interface FeatureRegistry {
  academics?: ComponentType<FeatureScreenProps>;
  learning?: ComponentType<FeatureScreenProps>;
}
export type { ApiClient, RequestOptions } from '../lib/api/client';
export { ApiError } from '../lib/api/client';
export type { CurrentUser, EntertainmentVideo, PlaybackSource } from '../contracts/generated';
export { useAuth } from '../state/AuthProvider';
export { theme } from '../theme';
export { Button } from '../components/Button';
