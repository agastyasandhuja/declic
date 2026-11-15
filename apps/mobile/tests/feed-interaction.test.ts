import test from 'node:test';
import assert from 'node:assert/strict';
import { FeedInteraction, scrubTarget } from '../src/lib/playback/FeedInteraction';
import { VisibleWatchTracker } from '../src/lib/playback/VisibleWatchTracker';
import { seekFeedVideo, waitForNativeSeek } from '../src/features/feed/FeedSeek';
import { parseCommentsPage } from '../src/features/feed/commentsData';

test('edge hold temporarily doubles speed and hides chrome; every exit restores normal playback', () => {
  const rates: number[] = [];
  const gestures = new FeedInteraction(() => {}, value => rates.push(value));
  gestures.hold('edge'); assert.equal(gestures.state.speed, 1);
  gestures.observe('clip-one', true); gestures.hold('edge');
  assert.equal(gestures.state.speed, 2); assert.equal(gestures.state.hidden, true);
  gestures.release(); assert.equal(gestures.state.speed, 1); assert.equal(gestures.state.hidden, false);
  gestures.hold('edge'); gestures.observe('clip-two', true); assert.equal(gestures.state.speed, 1);
  gestures.hold('edge'); gestures.observe('clip-two', false); assert.equal(gestures.state.speed, 1);
  gestures.observe('clip-two', true); gestures.hold('edge'); gestures.reset(); assert.equal(gestures.state.speed, 1);
  gestures.hold('edge'); gestures.dispose(); assert.equal(rates.at(-1), 1); assert.equal(gestures.state.hidden, false);
  gestures.hold('edge'); assert.equal(gestures.state.speed, 1);
});

test('menus, comments, scrubbing and quizzes prevent a hidden fast-playing state', () => {
  const gestures = new FeedInteraction(() => {}, () => {}); gestures.observe('clip', true);
  gestures.hold('center'); assert.equal(gestures.state.menu, true); assert.equal(gestures.state.hidden, false);
  gestures.hold('edge'); assert.equal(gestures.state.speed, 1);
  gestures.release(); assert.equal(gestures.state.menu, true);
  gestures.closeOverlay(); gestures.hold('edge'); gestures.openComments();
  assert.equal(gestures.state.speed, 1); assert.equal(gestures.state.comments, true);
  gestures.closeOverlay(); gestures.scrub(true); gestures.hold('edge'); assert.equal(gestures.state.speed, 1);
  gestures.scrub(false); gestures.observe(null, true); gestures.hold('center'); assert.equal(gestures.state.menu, false);
});

test('double speed credits only visible wall time; scrubbing and discontinuous seeks add nothing', () => {
  const watch = new VisibleWatchTracker();
  watch.sample(0, 0, true, 100000, 2); watch.sample(1000, 500, true, 100000, 2);
  assert.equal(watch.totalMs, 500);
  watch.sample(1000, 1000, false, 100000, 2); watch.sample(50000, 1500, false, 100000, 2);
  watch.sample(50000, 2000, true, 100000, 1); assert.equal(watch.totalMs, 500);
  watch.sample(50500, 2500, true, 100000, 1); assert.equal(watch.totalMs, 1000);
  watch.sample(70000, 3000, true, 100000, 2); assert.equal(watch.totalMs, 1000);
  assert.equal(scrubTarget(-5, 100, 40), 0); assert.equal(scrubTarget(50, 100, 40), 20);
  assert.equal(scrubTarget(200, 100, 40), 39.95); assert.equal(scrubTarget(1, 0, 40), null);
});

test('a native seek waits for queued progress and an accepted zero-credit anchor; late selection changes are fenced', async () => {
  let finishFlush!: () => void; let accept!: (value: any) => void;
  let sent: any; let seeks = 0; let current = true;
  const operation = seekFeedVideo({
    api: { request: async (_path, options) => { sent = options!.body; return await new Promise(resolve => { accept = resolve; }); } },
    events: { flush: () => new Promise<void>(resolve => { finishFlush = resolve; }) },
    sessionId: 'session', itemId: 'item', eventId: 'seek', positionMs: 2000, visibleWatchMs: 5000,
    isActive: () => true, isCurrent: () => current, onSeek: () => { seeks++; },
  });
  assert.equal(sent, undefined); finishFlush(); await Promise.resolve(); await Promise.resolve();
  assert.equal((sent as any)[0].event_type, 'playback_seeked'); assert.deepEqual((sent as any)[0].payload, { position_ms: 2000, visible_watch_ms: 5000 });
  assert.equal(seeks, 0); current = false; accept({ accepted_event_ids: ['seek'], rejected: [] });
  assert.equal(await operation, false); assert.equal(seeks, 0);
});

test('rejected seek cannot move media or bypass the quiz gate', async () => {
  await assert.rejects(seekFeedVideo({ api: { request: async () => ({ accepted_event_ids: [], rejected: [{ event_id: 'seek', code: 'QUIZ_REQUIRED' }] }) as any }, events: { flush: async () => {} }, sessionId: 'session', itemId: 'item', eventId: 'seek', positionMs: 0, visibleWatchMs: 5000, isActive: () => true, isCurrent: () => true, onSeek: () => assert.fail('rejected seek moved video') }));
});

test('comments accept real bounded fields and reject malformed/duplicated provider content', () => {
  const page = { schema_version: '1', availability: 'available', items: [{ comment_id: 'one', text: 'Synthetic comment', author: { username: 'synthetic' }, like_count: 2 }], next_cursor: null };
  assert.equal(parseCommentsPage(page).items.length, 1);
  assert.throws(() => parseCommentsPage({ ...page, items: [...page.items, ...page.items] }));
  assert.throws(() => parseCommentsPage({ ...page, items: [{ ...page.items[0], like_count: -1 }] }));
  assert.equal(parseCommentsPage({ ...page, availability: 'unavailable', items: [] }).availability, 'unavailable');
});


test('native seek waits across old frames and stops polling after a swipe', async () => {
  let position = 31, polls = 0;
  const wait = async () => { if (++polls === 3) position = 5.07; };
  assert.equal(await waitForNativeSeek(5, () => position, () => true, wait), true);
  assert.equal(polls, 3);
  const afterSwipe = await waitForNativeSeek(20, () => position, () => polls < 4, wait);
  assert.equal(afterSwipe, false);
  assert.equal(polls, 4);
});
