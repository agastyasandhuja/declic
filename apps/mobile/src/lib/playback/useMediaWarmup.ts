import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { AppState, Platform } from 'react-native';
import { useVideoPlayer } from 'expo-video';
import { cachedVideoSource, isMediaCacheEnabled } from './MediaCache';
import { MediaWarmup, type WarmAsset } from './MediaWarmup';

/** An unattached third player warms up to six MP4 starts into Expo's native LRU.
 * It never plays and cannot replace either of the two visible feed buffers. */
export function useMediaWarmup(assets: WarmAsset[], enabled: boolean) {
  const [memoryLimited, setMemoryLimited] = useState(false);
  const warmer = useVideoPlayer(null, player => {
    player.muted = true; player.volume = 0; player.staysActiveInBackground = false;
    player.bufferOptions = { preferredForwardBufferDuration: 2, waitsToMinimizeStalling: false };
  });
  const alive = useMemo(() => ({ current: true }), [warmer]);
  const queue = useMemo(() => new MediaWarmup({
    stop() { if (alive.current) { warmer.pause(); void warmer.replaceAsync(null).catch(() => undefined); } },
    async warm(url, signal) {
      if (!alive.current || signal.aborted || Platform.OS === 'web') return;
      const cancel = () => { if (alive.current) { warmer.pause(); void warmer.replaceAsync(null).catch(() => undefined); } };
      signal.addEventListener('abort', cancel, { once: true });
      const deadlineTimer = setTimeout(cancel, 6000);
      try {
        await warmer.replaceAsync(cachedVideoSource(url));
        const deadline = Date.now() + 5000;
        // readyToPlay only promises metadata/decodability; wait for buffered bytes.
        while (alive.current && !signal.aborted && Date.now() < deadline && warmer.status !== 'error' && warmer.bufferedPosition < 2) await new Promise(resolve => setTimeout(resolve, 100));
      } finally {
        clearTimeout(deadlineTimer); signal.removeEventListener('abort', cancel);
        if (alive.current) { warmer.pause(); await warmer.replaceAsync(null); }
      }
    },
  }), [warmer, alive]);
  const key = JSON.stringify(assets);
  useEffect(() => { queue.update(JSON.parse(key), enabled && !memoryLimited && isMediaCacheEnabled() && Platform.OS !== 'web'); }, [queue, key, enabled, memoryLimited]);
  useEffect(() => {
    const memory = AppState.addEventListener('memoryWarning', () => { queue.update([], false); setMemoryLimited(true); });
    const state = AppState.addEventListener('change', value => { if (value !== 'active') queue.update([], false); });
    return () => { memory.remove(); state.remove(); };
  }, [queue]);
  useLayoutEffect(() => { alive.current = true; return () => { queue.dispose(); alive.current = false; }; }, [queue, alive]);
}
