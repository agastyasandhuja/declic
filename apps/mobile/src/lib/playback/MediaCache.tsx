import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, View } from 'react-native';
import { clearVideoCacheAsync, setVideoCacheSizeAsync } from 'expo-video';
import * as SecureStore from 'expo-secure-store';
import { theme } from '../../theme';
import { MediaCachePolicy } from './MediaCachePolicy';

let caching = false;
const ownerKey = 'declic.media-cache-owner.v1';
const policy = new MediaCachePolicy({
  configure: bytes => setVideoCacheSizeAsync(bytes),
  readOwner: () => SecureStore.getItemAsync(ownerKey),
  writeOwner: owner => owner ? SecureStore.setItemAsync(ownerKey, owner) : SecureStore.deleteItemAsync(ownerKey),
  async clear() {
    // Expo releases the previous screen's players during effect cleanup.
    for (let attempt = 0; ; attempt++) {
      try { await clearVideoCacheAsync(); return; }
      catch (error) { if (attempt >= 3) throw error; await new Promise(resolve => setTimeout(resolve, 75)); }
    }
  },
});
export function isMediaCacheEnabled() { return caching; }
export function cachedVideoSource(uri: string | null) { return uri ? { uri, useCaching: caching } : null; }

/** The previous players unmount before another account's cache is prepared.
 * Only an owner/API marker persists, never feed cards or their signed URLs.
 * A cold start still fetches a fresh authenticated session and quiz gate. */
export function MediaCacheBoundary({ owner, children }: React.PropsWithChildren<{ owner: string | null }>) {
  const [ready, setReady] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    let alive = true; caching = false;
    const prepared = Platform.OS === 'web' ? Promise.resolve(false) : policy.prepare(owner);
    void prepared.then(enabled => { if (alive) { caching = enabled; setReady(owner); } });
    return () => { alive = false; caching = false; };
  }, [owner]);
  if (owner && ready !== owner) return <View style={{ flex: 1, backgroundColor: theme.colors.background, justifyContent: 'center' }}><ActivityIndicator color={theme.colors.accent} /></View>;
  return <>{children}</>;
}
