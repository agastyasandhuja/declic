import * as Crypto from 'expo-crypto';
import { starterMedia } from '../../lib/playback/MediaCache';
import { FeedBootstrap } from './FeedBootstrap';
export const feedBootstrap = new FeedBootstrap({
  preferred: scope => starterMedia.preferred(scope),
  authorize: (scope, page) => starterMedia.authorize(scope, page.items),
  requestId: () => Crypto.randomUUID(),
});
