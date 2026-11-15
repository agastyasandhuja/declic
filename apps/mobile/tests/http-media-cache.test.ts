import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { HttpMediaCache, type MediaFileEntry, type MediaFileStore } from '../src/lib/playback/HttpMediaCache';

const tick = () => new Promise<void>(resolve => setImmediate(resolve));
const url = (name: string) => `https://media.example/${name}.mp4?signature=private`;
function fixture() {
  const files = new Set<string>(); let entries: MediaFileEntry[] = []; let clock = 100000;
  const requests: { key: string; signal: AbortSignal; finish(bytes?: number): void }[] = [];
  const store: MediaFileStore = {
    key: async value => createHash('sha256').update(value).digest('hex'), uri: key => `file:///cache/${key}.mp4`,
    load: async () => structuredClone(entries), save: async value => { entries = structuredClone(value); },
    exists: async key => files.has(key), remove: async key => { files.delete(key); }, clear: async () => { files.clear(); entries = []; },
    download: (_url, key, signal) => new Promise(resolve => { requests.push({ key, signal, finish(bytes = 8) { files.add(key); resolve(bytes); } }); }),
  };
  return { store, files, requests, now: () => clock, advance: (ms: number) => { clock += ms; }, entries: () => entries };
}

test('only complete files resolve locally; completed bytes survive reopen without persisted URLs', async () => {
  const f = fixture(), cache = new HttpMediaCache(f.store, f.now, 24, 8); await cache.open();
  const work = cache.warm(url('a'), null, new AbortController().signal); await tick();
  assert.equal(await cache.resolve(url('a')), url('a'));
  f.requests[0].finish(); await work; assert.match(await cache.resolve(url('a')), /^file:/);
  assert.ok(!JSON.stringify(f.entries()).includes('signature')); assert.ok(!JSON.stringify(f.entries()).includes('https:'));
  cache.deactivate(); assert.equal(await cache.resolve(url('a')), url('a')); await cache.open();
  assert.match(await cache.resolve(url('a')), /^file:/);
  assert.equal(await cache.resolve(url('a') + 'changed'), url('a') + 'changed');
  await cache.discard(url('a')); assert.equal(await cache.resolve(url('a')), url('a'));
});

test('owner transition cancels in-flight work and late completion cannot populate the new cache', async () => {
  const f = fixture(), cache = new HttpMediaCache(f.store, f.now, 24, 8); await cache.open();
  const old = cache.warm(url('private-old-owner'), null, new AbortController().signal); await tick();
  const cleared = cache.clear(); assert.equal(f.requests[0].signal.aborted, true);
  const reopening = cache.open(); f.requests[0].finish(); await old; await cleared; await reopening;
  assert.equal(await cache.resolve(url('private-old-owner')), url('private-old-owner')); assert.equal(f.files.size, 0);
});

test('background/window cancellation, oversized files and expired URLs never become playback hits', async () => {
  const f = fixture(), cache = new HttpMediaCache(f.store, f.now, 24, 8); await cache.open();
  const abort = new AbortController(); const work = cache.warm(url('a'), null, abort.signal); await tick(); abort.abort();
  assert.equal(f.requests[0].signal.aborted, true); f.requests[0].finish(); await work; assert.equal(await cache.resolve(url('a')), url('a'));
  const large = cache.warm(url('b'), null, new AbortController().signal); await tick(); f.requests[1].finish(9); await large;
  assert.equal(await cache.resolve(url('b')), url('b')); assert.equal(f.files.size, 0);
  await cache.warm(url('expired'), new Date(f.now() + 1000).toISOString(), new AbortController().signal); assert.equal(f.requests.length, 2);
  const valid = cache.warm(url('c'), new Date(f.now() + 60000).toISOString(), new AbortController().signal); await tick(); f.requests[2].finish(); await valid;
  f.advance(60001); assert.equal(await cache.resolve(url('c')), url('c'));
});

test('downloads serialize and LRU eviction preserves retained player files until release', async () => {
  const f = fixture(), cache = new HttpMediaCache(f.store, f.now, 24, 8); await cache.open();
  const works = ['a', 'b', 'c'].map(name => cache.warm(url(name), null, new AbortController().signal));
  await tick(); assert.equal(f.requests.length, 1);
  for (let index = 0; index < 3; index++) { f.requests[index].finish(); await works[index]; await tick(); }
  await cache.resolve(url('a')); await cache.resolve(url('b'));
  const next = cache.warm(url('d'), null, new AbortController().signal); await tick(); f.requests[3].finish(); await next;
  assert.match(await cache.resolve(url('a')), /^file:/); assert.match(await cache.resolve(url('b')), /^file:/);
  assert.equal(await cache.resolve(url('c')), url('c')); assert.equal(f.files.size, 3);
  assert.equal(f.entries().reduce((sum, entry) => sum + entry.bytes, 0), 24);
  await cache.release(url('a')); await cache.release(url('a')); // Two resolved references above.
  const final = cache.warm(url('e'), null, new AbortController().signal); await tick(); f.requests[4].finish(); await final;
  assert.equal(await cache.resolve(url('a')), url('a')); assert.match(await cache.resolve(url('b')), /^file:/);
});

test('old same-URL file release cannot unpin its newly downloaded replacement', async () => {
  const f = fixture(), cache = new HttpMediaCache(f.store, f.now, 8, 8); await cache.open();
  const first = cache.warm(url('a'), null, new AbortController().signal); await tick(); f.requests[0].finish(); await first;
  await cache.resolve(url('a')); await cache.discard(url('a'));
  const retry = cache.warm(url('a'), null, new AbortController().signal); await tick(); f.requests[1].finish(); await retry;
  await cache.resolve(url('a')); await cache.release(url('a'));
  await assert.rejects(cache.warm(url('b'), null, new AbortController().signal), /budget/);
  assert.equal(f.files.size, 1); assert.equal(f.requests.length, 2);
  await cache.release(url('a'));
  const next = cache.warm(url('b'), null, new AbortController().signal); await tick(); f.requests[2].finish(); await next;
  assert.equal(await cache.resolve(url('a')), url('a'));
});

test('late URL hashing cannot resolve or discard bytes belonging to a new owner epoch', async () => {
  const f = fixture(), cache = new HttpMediaCache(f.store, f.now, 24, 8); await cache.open();
  const work = cache.warm(url('a'), null, new AbortController().signal); await tick(); f.requests[0].finish(); await work;
  const originalKey = f.store.key; let release!: (key: string) => void;
  f.store.key = () => new Promise(resolve => { release = resolve; });
  const pending = cache.resolve(url('a')); await tick(); cache.deactivate(); await cache.open();
  release(await originalKey(url('a'))); assert.equal(await pending, url('a'));
  const discard = cache.discard(url('a')); await tick(); cache.deactivate(); await cache.open();
  release(await originalKey(url('a'))); await discard; f.store.key = originalKey;
  assert.match(await cache.resolve(url('a')), /^file:/);
});
