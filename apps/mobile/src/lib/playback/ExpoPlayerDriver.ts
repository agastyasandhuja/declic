import type { VideoPlayer, VideoSource } from 'expo-video';
import type { PlayerDriver } from './SinglePlayerController';
const sourceUri = (source: VideoSource) => typeof source === 'string' ? source : source && typeof source === 'object' ? source.uri : null;

/** Expo iOS resolves replaceAsync before its main-queue item application. Wait
 * for the matching source AND native readiness, not merely the JS promise. */
export function createExpoPlayerDriver(player: VideoPlayer, source: (uri: string) => VideoSource | Promise<VideoSource>, discard?: (uri: string) => void | Promise<void>, release?: (uri: string, selected: VideoSource) => void | Promise<void>): PlayerDriver {
  let disposed = false;
  let retained: { uri: string; source: VideoSource } | null = null;
  const cancellations = new Set<() => void>();
  const releaseFile = async (file: { uri: string; source: VideoSource } | null) => { if (file) await release?.(file.uri, file.source); };
  const load = (selected: VideoSource) => new Promise<void>((resolve, reject) => {
    let applied = false, settled = false;
    const expected = sourceUri(selected);
    const subscriptions: { remove(): void }[] = [];
    const finish = (error?: Error) => {
      if (settled) return; settled = true; clearTimeout(timer); cancellations.delete(cancel);
      subscriptions.forEach(subscription => subscription.remove());
      if (error) reject(error); else resolve();
    };
    const cancel = () => finish(new Error('Player disposed'));
    const ready = () => {
      if (!applied) return;
      if (player.status === 'error') finish(new Error('Video source failed'));
      else if (player.status === 'readyToPlay') finish();
    };
    const timer = setTimeout(() => finish(new Error('Video source readiness timed out')), 12000);
    cancellations.add(cancel);
    try {
      if (disposed) { cancel(); return; }
      subscriptions.push(player.addListener('sourceChange', event => { applied = sourceUri(event.source) === expected; ready(); }));
      subscriptions.push(player.addListener('statusChange', ready));
      void player.replaceAsync(selected).then(ready, () => finish(new Error('Video source failed')));
    } catch { finish(new Error('Video source failed')); }
  });
  return {
    play: () => player.play(), pause: () => player.pause(),
    setMuted: muted => { if (player.muted !== muted) player.muted = muted; },
    setRate: rate => { if (player.playbackRate !== rate) player.playbackRate = rate; },
    seekTo: seconds => { player.currentTime = seconds; },
    async replaceAsync(uri) {
      if (disposed) throw new Error('Player disposed');
      const selected = await source(uri);
      let pending = sourceUri(selected)?.startsWith('file:') ? { uri, source: selected } : null;
      const releasePending = async () => { const value = pending; pending = null; await releaseFile(value); };
      try {
        if (disposed) throw new Error('Player disposed');
        try { await load(selected); }
        catch (error) {
          if (!pending || disposed) throw error;
          await releasePending();
          // The failed file is no longer usable. Never re-resolve it on fallback.
          const previous = retained; retained = null; await releaseFile(previous);
          if (disposed) throw new Error('Player disposed');
          await discard?.(uri);
          if (disposed) throw new Error('Player disposed');
          await load({ uri, useCaching: false });
        }
        if (disposed) throw new Error('Player disposed');
        const previous = retained; retained = pending; pending = null;
        await releaseFile(previous); // The replacement is now truly ready.
      } catch (error) { await releasePending(); throw error; }
    },
    dispose() {
      if (disposed) return; disposed = true;
      for (const cancel of [...cancellations]) cancel();
      const previous = retained; retained = null; void releaseFile(previous).catch(() => undefined);
    },
  };
}
