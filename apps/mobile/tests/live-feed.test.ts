import { test } from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../../../fixtures/entertainment/feed.json';
import { FeedHistory, appendFeedWindow, shouldPrefetchPage } from '../src/features/feed/source';
import { parseFeedPage } from '../src/contracts/validate';

const sample = parseFeedPage(fixture).items[0];
const clip = (id: number) => ({ ...sample, video_id: `synthetic_${id}`, provider_video_id: `${id}` });

test('a 250-clip feed retains the selected asset and every upcoming clip with bounded metadata', () => {
  let window = { items: Array.from({ length: 5 }, (_, i) => clip(i)), index: 0, removed: 0 };
  const visited: string[] = [];
  for (let id = 0; id < 250; id++) {
    assert.equal(window.items[window.index].video_id, `synthetic_${id}`);
    visited.push(window.items[window.index].video_id);
    if (window.items.length - window.index <= 3) {
      const last = Number(window.items.at(-1)!.provider_video_id);
      const current = window.items[window.index];
      window = appendFeedWindow(window.items, Array.from({ length: 5 }, (_, i) => clip(last + 1 + i)), window.index);
      assert.equal(window.items[window.index], current);
    }
    assert.ok(window.items.length <= 100);
    window.index++;
  }
  assert.equal(new Set(visited).size, 250);
});

test('rolling pages deduplicate both identities and never evict current or unseen clips', () => {
  const existing = Array.from({ length: 10 }, (_, i) => clip(i));
  const collision = { ...clip(11), video_id: existing[5].video_id };
  const window = appendFeedWindow(existing, [clip(9), collision, clip(10), clip(11)], 7, 10);
  assert.equal(window.removed, 2);
  assert.equal(window.index, 5);
  assert.equal(window.items[window.index], existing[7]);
  assert.deepEqual(window.items.slice(window.index + 1).map(item => item.video_id), ['synthetic_8', 'synthetic_9', 'synthetic_10', 'synthetic_11']);
  assert.throws(() => appendFeedWindow(existing, [clip(10)], 0, 10));
});

test('prefetch runs near the end only while visible, foregrounded, idle and healthy', () => {
  const state = { index: 2, count: 5, hasNext: true, focused: true, foreground: true, loading: false, hasError: false };
  assert.ok(shouldPrefetchPage(state));
  for (const patch of [{ index: 0, count: 10 }, { count: 0 }, { hasNext: false }, { focused: false }, { foreground: false }, { loading: true }, { hasError: true }]) {
    assert.equal(shouldPrefetchPage({ ...state, ...patch }), false);
  }
});


test('session history excludes watched clips after a reload or rolling window eviction', () => {
  const history = new FeedHistory();
  history.remember(clip(1));
  assert.deepEqual(history.unseen([clip(1), clip(2)]).map(v => v.video_id), ['synthetic_2']);
  // Provider identities survive a new internal ID or renewed signed URL.
  assert.equal(history.unseen([{ ...clip(1), video_id: 'another-id' }]).length, 0);
  assert.equal(history.unseen([clip(2)]).length, 1); // Prefetch does not mark it watched.
});

test('history stays bounded and initial short batches prefetch before the first swipe', () => {
  const history = new FeedHistory(2);
  history.remember(clip(1)); history.remember(clip(2)); history.remember(clip(3));
  assert.deepEqual(history.unseen([clip(1), clip(2), clip(3)]).map(v => v.video_id), ['synthetic_1']);
  assert.equal(shouldPrefetchPage({ index: 0, count: 4, hasNext: true, focused: true, foreground: true, loading: false, hasError: false }), true);
});
