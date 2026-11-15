import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, View } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { theme } from '../../theme';
import { StarterMedia } from './StarterMedia';
import { MediaCachePolicy } from './MediaCachePolicy';
import { clearNativeMediaFiles, nativeMediaFiles } from './NativeMediaFiles';

const starterKey = 'declic.media-starters.v1';
export const starterMedia = new StarterMedia(nativeMediaFiles, {
  read: () => SecureStore.getItemAsync(starterKey),
  write: value => value ? SecureStore.setItemAsync(starterKey, value) : SecureStore.deleteItemAsync(starterKey),
});
let caching = false;
const ownerKey = 'declic.media-cache-owner.v2';
const policy = new MediaCachePolicy({
  readOwner: () => SecureStore.getItemAsync(ownerKey),
  writeOwner: owner => owner ? SecureStore.setItemAsync(ownerKey, owner) : SecureStore.deleteItemAsync(ownerKey),
  clear: clearNativeMediaFiles,
});
export function isMediaCacheEnabled() { return caching; }
const releases = new WeakMap<object, () => Promise<void>>();
export async function cachedVideoSource(uri: string | null) {
  if (!uri) return null;
  const epoch = nativeMediaFiles.generation;
  const key = caching ? starterMedia.keyFor(uri) : undefined;
  const resolved = caching ? await (key ? nativeMediaFiles.resolveKey(key, epoch).then(value => value ?? uri) : nativeMediaFiles.resolve(uri)).catch(() => uri) : uri;
  const source = { uri: resolved, useCaching: false };
  if (resolved.startsWith('file:')) releases.set(source, () => key ? nativeMediaFiles.releaseKey(key, epoch) : nativeMediaFiles.release(uri, epoch));
  return source;
}
export async function discardCachedVideo(uri: string) { const key = starterMedia.keyFor(uri); starterMedia.forget(uri); await (key ? nativeMediaFiles.discardKey(key) : nativeMediaFiles.discard(uri)).catch(() => undefined); }
export async function releaseCachedVideo(_uri: string, source?: unknown) {
  if (!source || typeof source !== 'object') return;
  const release = releases.get(source); releases.delete(source);
  await release?.().catch(() => undefined);
}
let preparation: Promise<unknown> = Promise.resolve();

/** The previous players unmount before another account's cache is prepared.
 * Owner/API markers and bounded video/asset/hash hints persist, never feed cards,
 * quiz data or signed URLs. Retained bytes require fresh server authorization.
 * A cold start still fetches a fresh authenticated session and quiz gate. */
export function MediaCacheBoundary({ owner, children, onPrepared }: React.PropsWithChildren<{ owner: string | null; onPrepared?(): void }>) {
  const [ready, setReady] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    let alive = true; caching = false; nativeMediaFiles.deactivate(); starterMedia.deactivate();
    const prepared = preparation.catch(() => undefined).then(async () => {
      if (!alive || Platform.OS === 'web') return false;
      const enabled = await policy.prepare(owner);
      if (!alive) return false;
      if (!enabled) { await starterMedia.open(null).catch(() => undefined); return false; }
      try { await Promise.all([nativeMediaFiles.open(), starterMedia.open(owner).catch(() => undefined)]); return alive; } catch { return false; }
    });
    preparation = prepared;
    void prepared.then(enabled => { if (alive) { caching = enabled; onPrepared?.(); setReady(owner); } });
    return () => { alive = false; caching = false; nativeMediaFiles.deactivate(); starterMedia.deactivate(); };
  }, [owner, onPrepared]);
  if (owner && ready !== owner) return <View style={{ flex: 1, backgroundColor: theme.colors.background, justifyContent: 'center' }}><ActivityIndicator color={theme.colors.accent} /></View>;
  return <>{children}</>;
}
