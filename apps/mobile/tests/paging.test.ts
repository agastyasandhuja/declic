import { test } from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../../../fixtures/entertainment/feed.json';
import { parseFeedPage } from '../src/contracts/validate';
import type { FeedSource } from '../src/features/feed/source';
import { fetchAvailablePage, fetchRefillPage, abortableDelay } from '../src/features/feed/paging';
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
  assert.deepEqual(waits, [2000, 3000]);
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
  const result = await fetchAvailablePage(feed, [item], null, new AbortController().signal, value => checkpoints.push(value), async () => {});
  assert.equal(calls, 4);
  assert.equal(result.next_cursor, 'page_4');
  assert.equal(checkpoints.at(-1), 'page_4');
});

test('a permanent failure after an empty page retains the advanced cursor for manual retry', async () => {
  const checkpoints: unknown[] = [], calls: unknown[] = [];
  const feed = source(async cursor => {
    calls.push(cursor);
    if (cursor === 'old') return page([], 'advanced');
    throw new ApiError('Invalid cursor', 422, 'INVALID_CURSOR', false);
  });
  await assert.rejects(fetchAvailablePage(feed, [item], 'old', new AbortController().signal, value => checkpoints.push(value), async () => {}));
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

test('each duplicate page gets its own pacing budget instead of failing after the third deferral', async () => {
  const attempts = new Map<string, number>(); const calls: unknown[] = []; const waits: number[] = [];
  const feed = source(async cursor => {
    const key = cursor ?? 'page_0'; calls.push(key);
    const attempt = (attempts.get(key) ?? 0) + 1; attempts.set(key, attempt);
    if (attempt === 1) throw new ApiError('Pacing', 503, 'INSTAGRAM_BUSY', true, undefined, 2000);
    const number = Number(key.split('_')[1]);
    return page(number === 3 ? [fresh] : [item], `page_${number + 1}`);
  });
  const result = await fetchAvailablePage(feed, [item], 'page_0', new AbortController().signal, () => {}, async ms => { waits.push(ms); });
  assert.deepEqual(result.items, [fresh]);
  assert.equal(calls.length, 8);
  assert.equal(attempts.size, 4);
  assert.equal(waits.length, 7);
  assert.ok(waits.every(ms => ms === 2000));
});

test('temporary proxy/network failures retry the same cursor twice and respect provider cooldowns', async () => {
  const calls: unknown[] = [], waits: number[] = [];
  let attempt = 0;
  const feed = source(async cursor => {
    calls.push(cursor); attempt++;
    if (attempt === 1) throw new ApiError('Proxy', 503, 'PREVIEW_UNAVAILABLE', true);
    if (attempt === 2) throw new ApiError('Offline', 0, 'NETWORK_ERROR', true);
    return page([fresh], null);
  });
  const result = await fetchAvailablePage(feed, [item], 'same', new AbortController().signal, () => {}, async ms => { waits.push(ms); });
  assert.deepEqual(result.items, [fresh]);
  assert.deepEqual(calls, ['same', 'same', 'same']);
  assert.deepEqual(waits, [1000, 2000]);
  for (const hint of [undefined, 12000, 300000]) {
    let count = 0; const delays: number[] = [];
    const unavailable = source(async () => { count++; throw new ApiError('Unavailable', 503, 'INSTAGRAM_UNAVAILABLE', true, undefined, hint); });
    await assert.rejects(fetchAvailablePage(unavailable, [], null, new AbortController().signal, () => {}, async ms => { delays.push(ms); }));
    assert.equal(count, hint === 300000 ? 1 : 3);
    assert.deepEqual(delays, hint === 300000 ? [] : [hint ?? 30000, hint ?? 30000]);
  }
});

test('a new clip after more than four duplicate pages loads automatically without a manual retry', async () => {
  const cursors: unknown[] = [], checkpoints: unknown[] = [], waits: number[] = [];
  let count = 0;
  const feed = source(async cursor => {
    cursors.push(cursor); count++;
    return page(count === 6 ? [fresh] : [item], `page_${count}`);
  });
  const result = await fetchRefillPage(feed, [item], 'start', new AbortController().signal,
    cursor => checkpoints.push(cursor), async ms => { waits.push(ms); });
  assert.deepEqual(result.items, [fresh]);
  assert.deepEqual(cursors, ['start', 'page_1', 'page_2', 'page_3', 'page_4', 'page_5']);
  assert.equal(checkpoints.at(-1), 'page_5');
  assert.equal(count, 6);
  assert.equal(waits.length, 5);
});

test('automatic empty-window continuation stops after twelve pages and preserves the next cursor', async () => {
  let count = 0; const checkpoints: unknown[] = [], waits: number[] = [];
  const feed = source(async () => page([item], `page_${++count}`));
  const result = await fetchRefillPage(feed, [item], null, new AbortController().signal,
    cursor => checkpoints.push(cursor), async ms => { waits.push(ms); });
  assert.equal(count, 12);
  assert.equal(result.next_cursor, 'page_12');
  assert.equal(checkpoints.at(-1), 'page_12');
  assert.equal(waits.filter(ms => ms === 4000).length, 1);
  assert.equal(waits.length, 11);
});

test('rate limits bypass extra windows and background cancellation prevents the next window', async () => {
  let count = 0, waits = 0;
  const limited = source(async () => { count++; throw new ApiError('Rate limit', 503, 'INSTAGRAM_RATE_LIMITED', true); });
  await assert.rejects(fetchRefillPage(limited, [], null, new AbortController().signal, () => {}, async () => { waits++; }));
  assert.equal(count, 1); assert.equal(waits, 0);
  count = 0;
  const abort = new AbortController();
  const empty = source(async () => page([], `page_${++count}`));
  await assert.rejects(fetchRefillPage(empty, [], null, abort.signal, () => {}, async (ms, signal) => {
    waits++;
    if (waits === 4) { abort.abort(); await abortableDelay(ms, signal); }
  }));
  assert.equal(count, 4);
});
