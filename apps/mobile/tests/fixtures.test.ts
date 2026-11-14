import { test } from 'node:test';
import assert from 'node:assert/strict';
import edgeCases from '../../../fixtures/entertainment/edge-cases.json';
import user from '../../../fixtures/identity/current-user.json';
import { parseCurrentUser, parseFeedPage, parsePlayback } from '../src/contracts/validate';
import { eligibleVideos, createFixtureSource } from '../src/features/feed/source';

test('edge cases match the wire schema but duplicates, unavailable and expired items are not playable', () => {
  const page = parseFeedPage(edgeCases); assert.equal(page.items.length, 8);
  const ready = eligibleVideos(page.items); assert.equal(ready.length, 5); assert.ok(ready.every(item => item.duration_seconds === null));
  assert.equal(parseCurrentUser({ ...user, future_optional_field: 'accepted' }).user_id, 'user_demo_01');
});
test('credentials and non-HTTPS URLs are rejected from playback payloads', () => {
  const valid = edgeCases.items[0].playback;
  assert.throws(() => parsePlayback({ ...valid, headers_ref: 'private-session' }));
  assert.throws(() => parsePlayback({ ...valid, url: 'http://unsafe.example.test/clip.mp4' }));
});
test('fixture pages have a stable end and resolve stable video IDs', async () => {
  const source = createFixtureSource(); const first = await source.getPage(); const second = await source.getPage(first.next_cursor);
  assert.equal(first.items.length, 3); assert.equal(second.items.length, 2); assert.equal(second.next_cursor, null);
  assert.equal((await source.resolvePlayback(first.items[0].video_id)).asset_id, first.items[0].playback.asset_id);
  await assert.rejects(source.getPage('foreign-cursor')); await assert.rejects(source.resolvePlayback('missing'));
});
