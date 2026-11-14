import type { ApiClient } from '../../lib/api/client';

export interface FeedPlaybackEvent {
  event_id: string; session_id: string; item_id: string; event_type: string;
  client_occurred_at: string; payload: { position_ms: number; visible_watch_ms: number };
}

/** Preserves event identity and order across retries and concurrent flush callers. */
export class FeedEventBuffer {
  private events: FeedPlaybackEvent[] = [];
  private flight: Promise<void> | null = null;
  constructor(private api: ApiClient) {}
  add(event: FeedPlaybackEvent) {
    this.events.push(event);
    // An offline feed remains bounded. Drop complete old occurrences together,
    // rather than retaining progress whose required start event was discarded.
    while (this.events.length > 200) {
      const oldest = this.events[0].item_id;
      this.events = this.events.filter(item => item.item_id !== oldest);
    }
  }
  async flush(): Promise<void> {
    if (this.flight) await this.flight;
    if (!this.events.length) return;
    if (this.flight) return this.flush();
    const send = async () => {
      while (this.events.length) {
        const batch = this.events.slice(0, 100);
        const result = await this.api.request<{ accepted_event_ids: string[]; rejected: { event_id: string }[] }>('/v1/feed/events', {
          method: 'POST', body: batch, headers: { 'Idempotency-Key': batch[0].event_id },
        });
        const acknowledged = new Set([...result.accepted_event_ids, ...result.rejected.map(item => item.event_id)]);
        if (!batch.every(item => acknowledged.has(item.event_id))) throw new Error('Playback event acknowledgement was incomplete.');
        this.events = this.events.filter(item => !acknowledged.has(item.event_id));
      }
    };
    this.flight = send();
    try { await this.flight; } finally { this.flight = null; }
  }
}
