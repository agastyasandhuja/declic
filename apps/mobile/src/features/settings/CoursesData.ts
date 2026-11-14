import { ApiError, type ApiClient } from '../../lib/api/client';
import { parseAcademicProfile, type AcademicProfileView } from './academicData';

export interface CanvasConnection { status: 'connected' | 'disconnected' | 'reconnect_required' | 'error'; institution_origin?: string; last_sync_at?: string | null; job_id?: string }
export interface Preparation { academic_generation_configured: boolean; video_generation_enabled?: boolean; imports_and_lessons: Record<string, number>; videos: Record<string, number> }
export interface CoursesSnapshot {
  connection: CanvasConnection | null;
  profile: AcademicProfileView | null;
  preparation: Preparation | null;
  job: { state: string } | null;
  loading: boolean;
  error: string | null;
}

/** Session-local display data only. Independent sections publish as soon as ready. */
export class CoursesData {
  snapshot: CoursesSnapshot = { connection: null, profile: null, preparation: null, job: null, loading: false, error: null };
  private listeners = new Set<() => void>();
  private flight: Promise<void> | null = null;
  private abort: AbortController | null = null;
  private fullRefreshAt = -Infinity;
  constructor(private api: ApiClient, private now = Date.now) {}
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  getSnapshot = () => this.snapshot;
  private update(patch: Partial<CoursesSnapshot>) { this.snapshot = { ...this.snapshot, ...patch }; this.listeners.forEach(listener => listener()); }
  cancel() { this.abort?.abort(); this.abort = null; this.flight = null; this.update({ loading: false }); }
  load(force = false): Promise<void> {
    if (this.flight) {
      const pending = this.flight, active = this.abort;
      return force ? pending.then(() => { if (this.abort === active) return this.load(true); }) : pending;
    }
    const abort = new AbortController(); this.abort = abort;
    const current = () => this.abort === abort && !abort.signal.aborted;
    const full = force || !this.snapshot.connection || this.now() - this.fullRefreshAt >= 30000;
    this.update({ loading: true, error: null });
    const read = async <T,>(path: string, apply: (value: T) => void, absent?: T) => {
      try { const value = await this.api.request<T>(path, { signal: abort.signal }); if (current()) apply(value); }
      catch (problem) {
        if (!current()) return;
        if (problem instanceof ApiError && problem.status === 404 && absent !== undefined) apply(absent);
        else this.update({ error: problem instanceof Error ? problem.message : 'Unable to refresh courses. Please retry.' });
      }
    };
    const tasks: Promise<void>[] = [read<Preparation>('/v1/preparation', preparation => this.update({ preparation }))];
    const job = async (connection: CanvasConnection | null) => {
      if (!current()) return;
      if (!connection?.job_id) { this.update({ job: null }); return; }
      await read<{state: string}>(`/v1/academics/jobs/${encodeURIComponent(connection.job_id)}`, value => {
        if (this.snapshot.connection?.job_id === connection.job_id) this.update({ job: value });
      });
    };
    if (full) {
      tasks.push(read<unknown | null>('/v1/academics/profile', value => {
        this.update({ profile: value === null ? null : parseAcademicProfile(value) });
        this.fullRefreshAt = this.now();
      }, null));
      tasks.push(read<CanvasConnection>('/v1/canvas/connection', connection => {
        if (!['connected', 'disconnected', 'reconnect_required', 'error'].includes(connection.status)) throw new Error('Unable to read Canvas status. Please retry.');
        if (connection.job_id !== this.snapshot.connection?.job_id) this.update({ job: null });
        this.update({ connection });
      }).then(() => job(this.snapshot.connection)));
    } else if (!this.snapshot.job || !['succeeded', 'completed', 'failed', 'cancelled', 'ready'].includes(this.snapshot.job.state)) tasks.push(job(this.snapshot.connection));
    const flight = Promise.all(tasks).then(() => undefined).finally(() => {
      if (current()) { this.flight = null; this.update({ loading: false }); }
    });
    this.flight = flight;
    return flight;
  }
}

// A new API context or owner gets an empty snapshot. No disk cache, PAT or cookie.
const snapshots = new WeakMap<ApiClient, { owner: string; value: CoursesData }>();
export function coursesDataFor(api: ApiClient, owner: string) {
  const cached = snapshots.get(api);
  if (cached?.owner === owner) return cached.value;
  cached?.value.cancel();
  const value = new CoursesData(api); snapshots.set(api, { owner, value }); return value;
}
