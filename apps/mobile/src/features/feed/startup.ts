import { startupTrace } from '../../lib/playback/startupMetrics';
import * as Crypto from 'expo-crypto';
import { starterMedia } from '../../lib/playback/MediaCache';
import { FeedBootstrap } from './FeedBootstrap';
export const feedBootstrap = new FeedBootstrap({
  preferred: scope => starterMedia.preferred(scope),
  authorize: (scope, page) => starterMedia.authorize(scope, page.items),
  requestId: () => Crypto.randomUUID(),
  started: () => startupTrace.start(), received: page => { startupTrace.page(); if (page.items[0]?.kind === 'quiz') startupTrace.cancel(); }, cancelled: () => startupTrace.cancel(),
});
