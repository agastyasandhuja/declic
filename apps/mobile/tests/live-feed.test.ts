import { test } from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../../../fixtures/entertainment/feed.json';
import { appendFeedWindow, shouldPrefetchPage } from '../src/features/feed/source';
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

test('metadata prefetch fills eight upcoming clips only while visible, foregrounded, idle and healthy', () => {
  const state = { index: 2, count: 5, hasNext: true, focused: true, foreground: true, loading: false, hasError: false };
  assert.ok(shouldPrefetchPage(state));
  assert.ok(shouldPrefetchPage({ ...state, index: 0 }));
  assert.equal(shouldPrefetchPage({ ...state, index: 0, count: 9 }), false);
  assert.ok(shouldPrefetchPage({ ...state, index: 1, count: 9 }));
  for (const patch of [{ index: 0, count: 10 }, { count: 0 }, { hasNext: false }, { focused: false }, { foreground: false }, { loading: true }, { hasError: true }]) {
    assert.equal(shouldPrefetchPage({ ...state, ...patch }), false);
  }
});

test('a four-clip first page refills during the current clip and stops with eight ahead', () => {
  let window = { items: Array.from({ length: 4 }, (_, i) => clip(i)), index: 0, removed: 0 };
  const selected = window.items[0]; let calls = 0;
  while (shouldPrefetchPage({ index: 0, count: window.items.length, hasNext: true, focused: true,
    foreground: true, loading: false, hasError: false })) {
    window = appendFeedWindow(window.items, [clip(window.items.length)], 0);
    calls++;
    assert.ok(calls <= 5, 'Metadata refill must stop at its target.');
    assert.equal(window.items[0], selected);
  }
  assert.equal(window.items.length, 9);
  assert.equal(calls, 5);
});
