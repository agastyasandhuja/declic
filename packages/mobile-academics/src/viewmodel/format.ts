// Pure presentation logic for the academics UI (owner: Amogh).
//
// No React here, so it is unit-testable with `node --experimental-strip-types`.
// The components call these to decide labels/colors; keeping it pure means the
// display rules (never imply an invented date, keep suggested practice distinct)
// are tested independently of rendering.

import type {
  AcademicDate,
  CourseSummary,
  ImportStatus,
  LessonRequestView,
  ProfileCorrection,
} from '../api/types';

export function importStatusLabel(status: ImportStatus): string {
  switch (status) {
    case 'ready': return 'Ready';
    case 'needs_review': return 'Needs review';
    case 'partial': return 'Partial';
    case 'error': return 'Error';
    case 'queued': return 'Queued';
    case 'fetching': return 'Importing';
    case 'extracting': return 'Reading syllabus';
    case 'planning': return 'Planning lessons';
    default: return status;
  }
}

export type Tone = 'ok' | 'warn' | 'bad' | 'muted';

export function importStatusTone(status: ImportStatus): Tone {
  if (status === 'ready') return 'ok';
  if (status === 'error') return 'bad';
  if (status === 'needs_review' || status === 'partial') return 'warn';
  return 'muted';
}

// Real-time urgency line. Grounded in actual due dates; says nothing if none.
export function urgencyLabel(course: CourseSummary): string | null {
  const t = course.timing;
  if (!t || t.daysUntilNext === null || t.nextDueName === null) {
    return t && t.hasUndatedExam ? 'Exam listed (no date in Canvas)' : null;
  }
  const when =
    t.daysUntilNext <= 0 ? 'due today'
      : t.daysUntilNext === 1 ? 'due tomorrow'
        : `due in ${t.daysUntilNext} days`;
  return `Next: ${t.nextDueName} (${when})`;
}

// Sort most-urgent first; courses with no upcoming dated work sink to the bottom.
export function sortByUrgency(courses: CourseSummary[]): CourseSummary[] {
  return [...courses].sort(
    (a, b) => (b.timing?.urgency ?? 0) - (a.timing?.urgency ?? 0),
  );
}

// How a date should read on screen — never fabricates a time for a date-only item.
export function formatAcademicDate(d: AcademicDate): string {
  if (!d.date) return d.evidenceStatus === 'unknown' ? 'No date' : 'Date unknown';
  const suffix = d.evidenceStatus === 'inferred' ? ' (inferred)'
    : d.evidenceStatus === 'user_confirmed' ? ' (you confirmed)'
      : '';
  if (d.precision === 'datetime' && d.timestamp) return `${d.timestamp}${suffix}`;
  return `${d.date}${suffix}`;
}

export function lessonExamLabel(lesson: LessonRequestView): string {
  if (lesson.evidenceStatus === 'suggested_practice') return 'Suggested practice';
  switch (lesson.examScopeStatus) {
    case 'explicit': return 'On the exam';
    case 'user_confirmed': return 'On the exam (you confirmed)';
    case 'inferred': return 'Possibly on the exam';
    default: return 'Not exam-specific';
  }
}

// Build a corrections payload from edits, dropping no-ops. Used by the edit view
// so the same validation is testable without rendering.
export function buildCorrections(
  original: { assessmentId: string; date: string | null; scopeStatus: string }[],
  edits: Record<string, { date?: string | null; scopeStatus?: string }>,
): ProfileCorrection[] {
  const out: ProfileCorrection[] = [];
  for (const row of original) {
    const edit = edits[row.assessmentId];
    if (!edit) continue;
    const change: ProfileCorrection = { assessmentId: row.assessmentId };
    let touched = false;
    if (edit.date !== undefined && edit.date !== row.date) {
      change.date = edit.date;
      change.scopeStatus = 'user_confirmed';
      touched = true;
    }
    if (edit.scopeStatus !== undefined && edit.scopeStatus !== row.scopeStatus) {
      change.scopeStatus = edit.scopeStatus as ProfileCorrection['scopeStatus'];
      touched = true;
    }
    if (touched) out.push(change);
  }
  return out;
}

// Accept only YYYY-MM-DD (or empty to clear). Prevents a free-text date from
// becoming a fake precise timestamp downstream.
export function isValidDateInput(value: string): boolean {
  if (value === '') return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(value + 'T00:00:00Z');
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === value;
}
