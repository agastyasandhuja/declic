import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, View } from 'react-native';
import { clearVideoCacheAsync, setVideoCacheSizeAsync } from 'expo-video';
import * as SecureStore from 'expo-secure-store';
import { theme } from '../../theme';
import { MediaCachePolicy } from './MediaCachePolicy';
import { nativeMediaFiles } from './NativeMediaFiles';

let caching = false;
const ownerKey = 'declic.media-cache-owner.v2';
const policy = new MediaCachePolicy({
  configure: bytes => setVideoCacheSizeAsync(bytes),
  readOwner: () => SecureStore.getItemAsync(ownerKey),
  writeOwner: owner => owner ? SecureStore.setItemAsync(ownerKey, owner) : SecureStore.deleteItemAsync(ownerKey),
  async clear() {
    await nativeMediaFiles.clear();
    // Expo releases the previous screen's players during effect cleanup.
    for (let attempt = 0; ; attempt++) {
      try { await clearVideoCacheAsync(); return; }
      catch (error) { if (attempt >= 3) throw error; await new Promise(resolve => setTimeout(resolve, 75)); }
    }
  },
});
export function isMediaCacheEnabled() { return caching; }
const releases = new WeakMap<object, () => Promise<void>>();
export async function cachedVideoSource(uri: string | null) {
  if (!uri) return null;
  const epoch = nativeMediaFiles.generation;
  const resolved = caching ? await nativeMediaFiles.resolve(uri).catch(() => uri) : uri;
  const source = { uri: resolved, useCaching: false };
  if (resolved.startsWith('file:')) releases.set(source, () => nativeMediaFiles.release(uri, epoch));
  return source;
}
export async function discardCachedVideo(uri: string) { await nativeMediaFiles.discard(uri).catch(() => undefined); }
export async function releaseCachedVideo(_uri: string, source?: unknown) {
  if (!source || typeof source !== 'object') return;
  const release = releases.get(source); releases.delete(source);
  await release?.().catch(() => undefined);
}
let preparation: Promise<unknown> = Promise.resolve();

/** The previous players unmount before another account's cache is prepared.
 * Only an owner/API marker persists, never feed cards or their signed URLs.
 * A cold start still fetches a fresh authenticated session and quiz gate. */
export function MediaCacheBoundary({ owner, children }: React.PropsWithChildren<{ owner: string | null }>) {
  const [ready, setReady] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    let alive = true; caching = false; nativeMediaFiles.deactivate();
    const prepared = preparation.catch(() => undefined).then(async () => {
      if (!alive || Platform.OS === 'web') return false;
      const enabled = await policy.prepare(owner);
      if (!alive || !enabled) return false;
      try { await nativeMediaFiles.open(); return alive; } catch { return false; }
    });
    preparation = prepared;
    void prepared.then(enabled => { if (alive) { caching = enabled; setReady(owner); } });
    return () => { alive = false; caching = false; nativeMediaFiles.deactivate(); };
  }, [owner]);
  if (owner && ready !== owner) return <View style={{ flex: 1, backgroundColor: theme.colors.background, justifyContent: 'center' }}><ActivityIndicator color={theme.colors.accent} /></View>;
  return <>{children}</>;
}
