// Display adapter for the academic owner's current profile response. Dates retain
// their precision and timezone; unknown evidence never becomes a due-date claim.
export interface AcademicProfileView {
  courses: { course_id: string; title: string | null; import_status: string; missing_sources: string[] }[];
  units: { course_id: string; title: string }[];
  assessments: { course_id: string; title: string; dateLabel: string }[];
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Course data is unavailable. Please refresh.');
  return value as Record<string, unknown>;
}
function string(value: unknown) { if (typeof value !== 'string') throw new Error('Course data is incomplete. Please refresh.'); return value; }
function list(value: unknown): unknown[] { if (!Array.isArray(value)) throw new Error('Course data is incomplete. Please refresh.'); return value; }
export function parseAcademicProfile(value: unknown): AcademicProfileView {
  const profile = record(value);
  return {
    courses: list(profile.courses).map(value => { const c = record(value); return { course_id: string(c.course_id), title: c.title == null ? null : string(c.title), import_status: string(c.import_status), missing_sources: list(c.missing_sources ?? []).map(string) }; }),
    units: list(profile.units).map(value => { const u = record(value); return { course_id: string(u.course_id), title: string(u.title) }; }),
    assessments: list(profile.assessments).map(value => {
      const item = record(value), date = record(item.scheduled);
      const supported = ['explicit', 'user_confirmed'].includes(String(date.evidence_status));
      let dateLabel = 'Date needs confirmation';
      if (supported && date.precision === 'date' && typeof date.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date.date)) dateLabel = `${date.date} · ${typeof date.timezone === 'string' ? date.timezone : 'timezone unknown'} · date only`;
      else if (supported && date.precision === 'datetime' && typeof date.timestamp === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(date.timestamp) && Number.isFinite(Date.parse(date.timestamp))) dateLabel = `${date.timestamp}${typeof date.timezone === 'string' ? ` · ${date.timezone}` : ''}`;
      return { course_id: string(item.course_id), title: string(item.title), dateLabel };
    }),
  };
}
