import test from 'node:test';
import assert from 'node:assert/strict';
import { FeedEventBuffer, type FeedPlaybackEvent } from '../src/features/feed/FeedEventBuffer';

const event = (id: string): FeedPlaybackEvent => ({ event_id: id, session_id: 'session', item_id: 'clip', event_type: 'playback_progress', client_occurred_at: new Date().toISOString(), payload: { position_ms: 1000, visible_watch_ms: 1000 } });

test('failed delivery retries identical events in order, including progress added during the request', async () => {
  const batches: string[][] = []; let fail = true;
  const queue = new FeedEventBuffer({ request: async (_path, options) => {
    const ids = (options!.body as FeedPlaybackEvent[]).map(item => item.event_id); batches.push(ids);
    if (fail) { fail = false; queue.add(event('later')); throw new Error('offline'); }
    return { accepted_event_ids: ids, rejected: [] } as any;
  } });
  queue.add(event('first')); await assert.rejects(queue.flush());
  await queue.flush(); await queue.flush();
  assert.deepEqual(batches, [['first'], ['first', 'later']]);
});

test('feed and quiz flush callers wait for the same in-flight batch then all queued events', async () => {
  let release!: () => void; const gate = new Promise<void>(resolve => { release = resolve; });
  const batches: string[][] = [];
  const queue = new FeedEventBuffer({ request: async (_path, options) => {
    const ids = (options!.body as FeedPlaybackEvent[]).map(item => item.event_id); batches.push(ids);
    if (batches.length === 1) await gate;
    return { accepted_event_ids: ids, rejected: [] } as any;
  } });
  queue.add(event('started')); const first = queue.flush(); queue.add(event('skipped'));
  let secondComplete = false; const second = queue.flush().then(() => { secondComplete = true; });
  await Promise.resolve(); assert.equal(secondComplete, false); release();
  await Promise.all([first, second]); assert.deepEqual(batches, [['started'], ['skipped']]);
});

test('continuous progress during slow uploads cannot starve feed pagination; later events remain queued', async () => {
  const batches: string[][] = []; let number = 0;
  const queue = new FeedEventBuffer({ request: async (_path, options) => {
    if (++number > 5) throw new Error('unbounded draining');
    const ids = (options!.body as FeedPlaybackEvent[]).map(item => item.event_id); batches.push(ids);
    queue.add(event(`during-${number}`));
    return { accepted_event_ids: ids, rejected: [] } as any;
  } });
  queue.add(event('before-page'));
  await queue.flush();
  assert.deepEqual(batches, [['before-page']]);
  await queue.flush();
  assert.deepEqual(batches, [['before-page'], ['during-1']]);
});
