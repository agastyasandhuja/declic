import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { clearMediaCacheFiles } from '../src/lib/playback/MediaCacheCleanup';
import { MediaCachePolicy } from '../src/lib/playback/MediaCachePolicy';

test('cold cache opens when obsolete Expo folder never existed; cleanup preserves unrelated cache', async () => {
  const root = await mkdtemp(join(tmpdir(), 'declic-cache-'));
  try {
    const owned = join(root, 'declic-feed-files-v1');
    await writeFile(join(root, 'unrelated'), 'keep');
    // Installed Expo's old cleanup starts with this failing directory listing.
    await assert.rejects(readdir(join(root, 'expo-video-cache')), { code: 'ENOENT' });
    let owner: string | null = null;
    const policy = new MediaCachePolicy({
      readOwner: async () => owner, writeOwner: async next => { owner = next; },
      clear: () => clearMediaCacheFiles(() => rm(owned, { recursive: true, force: true }), `${root}/`,
        (uri, options) => rm(uri, { recursive: true, force: options.idempotent })),
    });
    assert.equal(await policy.prepare('api:alice'), true);
    await mkdir(owned, { recursive: true }); // NativeMediaFiles.open creates this directory.
    assert.deepEqual((await readdir(root)).sort(), ['declic-feed-files-v1', 'unrelated']);
    await mkdir(join(root, 'expo-video-cache')); await writeFile(join(owned, 'old.mp4'), 'old');
    assert.equal(await policy.prepare('api:bob'), true);
    assert.deepEqual(await readdir(root), ['unrelated']);
    assert.equal(owner, 'api:bob');
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('HTTP ownership cleanup failure never advances owner or enables cache', async () => {
  let owner: string | null = 'api:alice'; let deletes = 0;
  const policy = new MediaCachePolicy({
    readOwner: async () => owner, writeOwner: async next => { owner = next; },
    clear: () => clearMediaCacheFiles(async () => { throw new Error('HTTP cache inaccessible'); },
      'file:///cache/', async () => { deletes++; }),
  });
  assert.equal(await policy.prepare('api:bob'), false);
  assert.equal(owner, 'api:alice'); assert.equal(deletes, 0);
  assert.equal(await policy.prepare(null), false); assert.equal(owner, 'api:alice');
});
