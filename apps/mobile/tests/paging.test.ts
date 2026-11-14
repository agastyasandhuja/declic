import { test } from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../../../fixtures/entertainment/feed.json';
import { parseFeedPage } from '../src/contracts/validate';
import type { FeedSource } from '../src/features/feed/source';
import { fetchAvailablePage, abortableDelay } from '../src/features/feed/paging';
import { ApiError } from '../src/lib/api/client';

const item = parseFeedPage(fixture).items[0];
const fresh = { ...item, video_id: 'synthetic_new', provider_video_id: 'synthetic_new' };
const page = (items: typeof item[], next_cursor: string | null) => ({ schema_version: '1' as const, items, next_cursor });
const source = (getPage: FeedSource['getPage']): FeedSource => ({ mode: 'api', getPage, async resolvePlayback() { return item.playback; } });

test('duplicate windows checkpoint the next cursor and a paced retry does not restart or skip pages', async () => {
  const cursors: unknown[] = [], checkpoints: unknown[] = [], waits: number[] = [];
  let calls = 0;
  const feed = source(async cursor => {
    cursors.push(cursor); calls++;
    if (calls === 1) return page([item], 'page_two');
    if (calls === 2) throw new ApiError('Wait', 503, 'INSTAGRAM_BUSY', true, undefined, 3000);
    return page([fresh], 'page_three');
  });
  const result = await fetchAvailablePage(feed, [item], 'page_one', new AbortController().signal,
    value => checkpoints.push(value), async ms => { waits.push(ms); });
  assert.deepEqual(cursors, ['page_one', 'page_two', 'page_two']);
  assert.deepEqual(checkpoints, ['page_two']);
  assert.deepEqual(waits, [3000]);
  assert.deepEqual(result.items, [fresh]);
});

test('repeated busy responses have two bounded waits; rate limits and authentication errors are not polled', async () => {
  for (const code of ['INSTAGRAM_BUSY', 'INSTAGRAM_RATE_LIMITED', 'AUTH_REQUIRED']) {
    let calls = 0, waits = 0;
    const feed = source(async () => { calls++; throw new ApiError('Stopped', code === 'AUTH_REQUIRED' ? 401 : 503, code, code !== 'AUTH_REQUIRED'); });
    await assert.rejects(fetchAvailablePage(feed, [], null, new AbortController().signal, () => {}, async () => { waits++; }));
    assert.equal(calls, code === 'INSTAGRAM_BUSY' ? 3 : 1);
    assert.equal(waits, code === 'INSTAGRAM_BUSY' ? 2 : 0);
  }
});

test('long duplicate runs are bounded and preserve the continuation for explicit retry', async () => {
  let calls = 0; const checkpoints: unknown[] = [];
  const feed = source(async () => page([item], `page_${++calls}`));
  const result = await fetchAvailablePage(feed, [item], null, new AbortController().signal, value => checkpoints.push(value));
  assert.equal(calls, 4);
  assert.equal(result.next_cursor, 'page_4');
  assert.equal(checkpoints.at(-1), 'page_4');
});

test('a permanent failure after an empty page retains the advanced cursor for manual retry', async () => {
  const checkpoints: unknown[] = [], calls: unknown[] = [];
  const feed = source(async cursor => {
    calls.push(cursor);
    if (cursor === 'old') return page([], 'advanced');
    throw new ApiError('Offline', 0, 'NETWORK_ERROR', true);
  });
  await assert.rejects(fetchAvailablePage(feed, [item], 'old', new AbortController().signal, value => checkpoints.push(value)));
  assert.deepEqual(calls, ['old', 'advanced']);
  assert.deepEqual(checkpoints, ['advanced']);
});

test('cursor loops stop and background/unmount cancellation ends a scheduled wait', async () => {
  const feed = source(async () => page([], 'same_cursor'));
  await assert.rejects(fetchAvailablePage(feed, [], 'same_cursor', new AbortController().signal, () => {}), /repeated/);
  const abort = new AbortController();
  const waiting = abortableDelay(30000, abort.signal);
  abort.abort();
  await assert.rejects(waiting, /Cancelled/);
  let calls = 0;
  const background = new AbortController();
  const busy = source(async () => { calls++; throw new ApiError('Wait', 503, 'INSTAGRAM_BUSY', true); });
  await assert.rejects(fetchAvailablePage(busy, [], null, background.signal, () => {}, async (ms, signal) => {
    background.abort(); await abortableDelay(ms, signal);
  }), /Cancelled/);
  assert.equal(calls, 1);
});
