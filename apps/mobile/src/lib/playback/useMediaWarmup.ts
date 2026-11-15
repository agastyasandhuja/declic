import { useEffect, useMemo, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';
import { isMediaCacheEnabled, starterMedia } from './MediaCache';
import { MediaWarmup, type WarmAsset } from './MediaWarmup';
import { nativeMediaFiles } from './NativeMediaFiles';

/** Six complete upcoming MP4s over one foreground HTTP task. No extra player,
 * decoder or audio-session changes. The caller prioritizes current/next buffers. */
export function useMediaWarmup(assets: WarmAsset[], enabled: boolean) {
  const [memoryLimited, setMemoryLimited] = useState(false);
  const latest = useRef(assets); latest.current = assets;
  const queue = useMemo(() => new MediaWarmup({
    warm: async (url, signal) => {
      const asset = latest.current.find(item => item.url === url), epoch = nativeMediaFiles.generation;
      if (asset?.video_id && asset.asset_id && !await starterMedia.prepareWarm(asset.video_id, asset.asset_id, url)) return;
      if (signal.aborted || epoch !== nativeMediaFiles.generation) return;
      await nativeMediaFiles.warm(url, asset?.expires_at ?? null, signal);
      if (!signal.aborted && epoch === nativeMediaFiles.generation && asset?.video_id && asset.asset_id) await starterMedia.record(asset.video_id, asset.asset_id, url).catch(() => undefined);
    },
    stop() { /* Queue aborts its HTTP task; no native player to reset. */ },
  }), []);
  const key = JSON.stringify(assets);
  useEffect(() => { queue.update(JSON.parse(key), enabled && !memoryLimited && isMediaCacheEnabled() && Platform.OS !== 'web'); }, [queue, key, enabled, memoryLimited]);
  useEffect(() => {
    const memory = AppState.addEventListener('memoryWarning', () => { queue.update([], false); setMemoryLimited(true); });
    const state = AppState.addEventListener('change', value => { if (value !== 'active') queue.update([], false); });
    return () => { queue.dispose(); memory.remove(); state.remove(); };
  }, [queue]);
}
