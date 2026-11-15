import { useEffect, useRef, useState } from 'react';
import type { PlaybackSource } from '../../contracts/generated';
import type { BufferedPlayerController } from '../../lib/playback/BufferedPlayerController';
import { PLAYBACK_REFRESH_MARGIN_MS } from '../../lib/playback/PlaybackRecovery';
import { prepareUpcomingPlayback, type UpcomingPlaybackUpdate } from './upcomingPlayback';

export function useUpcomingPlayback<T>(
  item: T | undefined,
  source: PlaybackSource | undefined,
  controller: BufferedPlayerController,
  enabled: boolean,
  transitioning: boolean,
  resolve: (item: T, signal: AbortSignal) => Promise<PlaybackSource>,
  apply: (item: T, update: UpcomingPlaybackUpdate) => void,
) {
  const callbacks = useRef({ resolve, apply });
  callbacks.current = { resolve, apply };
  const [result, setResult] = useState<{ item: T; update: UpcomingPlaybackUpdate }>();
  useEffect(() => {
    if (!enabled || item === undefined || !source) return;
    const abort = new AbortController();
    let expiryTimer: ReturnType<typeof setTimeout> | undefined;
    const prepare = () => prepareUpcomingPlayback(source, controller, signal => callbacks.current.resolve(item, signal), abort.signal);
    const publish = (update: UpcomingPlaybackUpdate | undefined) => {
      if (update && !abort.signal.aborted) setResult({ item, update });
    };
    const refreshAt = Date.parse(source.expires_at ?? '') - PLAYBACK_REFRESH_MARGIN_MS;
    const untilRefresh = refreshAt - Date.now();
    void prepare().then(update => {
      publish(update);
      // A paused or looping current clip may outlive its standby's signed URL.
      if (!update && !abort.signal.aborted && untilRefresh > 0 && untilRefresh <= 2147483647) {
        expiryTimer = setTimeout(() => { void prepare().then(publish); }, Math.max(0, refreshAt - Date.now()));
      }
    });
    return () => { abort.abort(); clearTimeout(expiryTimer); };
  }, [item, source, controller, enabled]);
  useEffect(() => {
    if (!result || transitioning) return;
    if (enabled && result.item === item) callbacks.current.apply(result.item, result.update);
    setResult(undefined);
  }, [enabled, item, result, transitioning]);
}
