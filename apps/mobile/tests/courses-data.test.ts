import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, type ApiClient } from '../src/lib/api/client';
import { CoursesData, coursesDataFor } from '../src/features/settings/CoursesData';
const profile = { courses: [{ course_id: 'synthetic-course', title: 'Synthetic', import_status: 'ready' }], units: [], assessments: [] };
const preparation = { academic_generation_configured: true, imports_and_lessons: {}, videos: {} };
const settle = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };

test('course profile publishes before slow preparation and job; refresh callers coalesce', async () => {
  const pending = new Map<string, (value: unknown) => void>();
  const calls: string[] = [];
  const api: ApiClient = { request: path => { calls.push(path); return new Promise(resolve => pending.set(path, resolve as any)); } };
  const model = new CoursesData(api);
  const first = model.load(); assert.equal(model.load(), first);
  assert.equal(calls.length, 3);
  pending.get('/v1/academics/profile')!(profile); await settle();
  assert.equal(model.snapshot.profile?.courses[0].title, 'Synthetic');
  assert.equal(model.snapshot.loading, true);
  pending.get('/v1/canvas/connection')!({ status: 'connected', job_id: 'job' }); await settle();
  assert.equal(model.snapshot.connection?.status, 'connected');
  assert.ok(pending.has('/v1/academics/jobs/job'));
  pending.get('/v1/preparation')!(preparation);
  pending.get('/v1/academics/jobs/job')!({ state: 'running' }); await first;
  assert.equal(model.snapshot.loading, false);
});

test('tab reentry shows cached data and polls cheap status without repeating full profile; failures preserve sections', async () => {
  let now = 0; const calls: string[] = []; let fail = false;
  const api: ApiClient = { async request<T>(path: string) {
    calls.push(path);
    if (path === '/v1/preparation') { if (fail) throw new ApiError('Preparation unavailable', 503, 'BUSY', true); return preparation as T; }
    if (path === '/v1/canvas/connection') return { status: 'connected' } as T;
    return profile as T;
  } };
  const model = coursesDataFor(api, 'owner-a'); await model.load(); model.cancel();
  assert.equal(coursesDataFor(api, 'owner-a'), model);
  calls.length = 0; fail = true; await model.load();
  assert.deepEqual(calls, ['/v1/preparation']);
  assert.equal(model.snapshot.profile?.courses.length, 1); assert.equal(model.snapshot.error, 'Preparation unavailable');
  const timed = new CoursesData(api, () => now); fail = false; await timed.load(); calls.length = 0;
  now = 30001; await timed.load(); assert.ok(calls.includes('/v1/academics/profile'));
  assert.equal(coursesDataFor(api, 'owner-b').snapshot.profile, null);
  assert.equal(coursesDataFor({ ...api }, 'owner-a').snapshot.profile, null);
});

test('cancellation fences late responses without discarding cached data; forced refresh after mutation runs anew', async () => {
  let resolveOld!: (value: unknown) => void; let generation = 0; let calls = 0;
  const api: ApiClient = { async request<T>(path: string) {
    calls++;
    if (path === '/v1/academics/profile' && generation === 0) return await new Promise(resolve => { resolveOld = resolve as any; });
    if (path === '/v1/academics/profile') return profile as T;
    if (path === '/v1/canvas/connection') return { status: 'connected' } as T;
    return preparation as T;
  } };
  const model = new CoursesData(api); const old = model.load(); await settle(); model.cancel(); generation++;
  await model.load(); resolveOld({ ...profile, courses: [] }); await old;
  assert.equal(model.snapshot.profile?.courses.length, 1);
  const before = calls; const poll = model.load(); const forced = model.load(true); await Promise.all([poll, forced]);
  assert.equal(calls - before, 4, 'one cheap poll then three forced reads');
});

test('leaving the tab cancels a queued forced refresh instead of restarting hidden requests', async () => {
  let resolve!: (value: unknown) => void; let calls = 0;
  const api: ApiClient = { async request<T>(path: string) {
    calls++;
    if (path === '/v1/academics/profile') return await new Promise(done => { resolve = done as any; });
    return (path === '/v1/canvas/connection' ? { status: 'disconnected' } : preparation) as T;
  } };
  const model = new CoursesData(api); const initial = model.load(); const forced = model.load(true);
  model.cancel(); resolve(profile); await Promise.all([initial, forced]);
  assert.equal(calls, 3); assert.equal(model.snapshot.profile, null); assert.equal(model.snapshot.loading, false);
});


test('a succeeded import job is not polled again between full refreshes', async () => {
  const calls: string[] = [];
  const api: ApiClient = { async request<T>(path: string) {
    calls.push(path);
    if (path === '/v1/canvas/connection') return { status: 'connected', job_id: 'done' } as T;
    if (path === '/v1/academics/jobs/done') return { state: 'succeeded' } as T;
    if (path === '/v1/academics/profile') return profile as T;
    return preparation as T;
  } };
  const model = new CoursesData(api); await model.load(); calls.length = 0;
  await model.load();
  assert.deepEqual(calls, ['/v1/preparation']);
  assert.equal(model.snapshot.job?.state, 'succeeded');
});
