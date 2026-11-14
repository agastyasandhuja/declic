// Pure view-model tests. Run with:  node --experimental-strip-types tests/format.test.ts
import assert from 'node:assert/strict';
import test from 'node:test';
import type { AcademicDate, CourseSummary, LessonRequestView } from '../src/api/types.ts';
import {
  buildCorrections, formatAcademicDate, importStatusLabel, isValidDateInput,
  lessonExamLabel, sortByUrgency, urgencyLabel,
} from '../src/viewmodel/format.ts';

function course(id: string, urgency: number | null, days: number | null, name: string | null): CourseSummary {
  return {
    courseId: id, title: id, term: 'Fall 2026', timezone: 'America/New_York',
    importStatus: 'ready', missingSources: [],
    timing: urgency === null ? null : {
      nextDueName: name, nextDueDate: days === null ? null : '2026-11-17',
      daysUntilNext: days, upcomingCount: 1, urgency, hasUndatedExam: false, upcoming: [],
    },
  };
}

test('courses sort by urgency, untimed last', () => {
  const sorted = sortByUrgency([course('a', 0.3, 20, 'HW'), course('z', null, null, null), course('m', 0.9, 2, 'Quiz')]);
  assert.deepEqual(sorted.map((c) => c.courseId), ['m', 'a', 'z']);
});

test('urgency label is real or absent, never invented', () => {
  assert.equal(urgencyLabel(course('a', 0.9, 2, 'Quiz 8')), 'Next: Quiz 8 (due in 2 days)');
  assert.equal(urgencyLabel(course('a', 0.9, 1, 'Quiz 8')), 'Next: Quiz 8 (due tomorrow)');
  assert.equal(urgencyLabel(course('a', 0.9, 0, 'Quiz 8')), 'Next: Quiz 8 (due today)');
  assert.equal(urgencyLabel(course('z', null, null, null)), null);
});

test('date formatting never fabricates a time', () => {
  const dateOnly: AcademicDate = { date: '2026-10-14', timestamp: null, timezone: 'America/New_York', precision: 'date', evidenceStatus: 'explicit' };
  assert.equal(formatAcademicDate(dateOnly), '2026-10-14');
  const unknown: AcademicDate = { date: null, timestamp: null, timezone: null, precision: 'unknown', evidenceStatus: 'unknown' };
  assert.equal(formatAcademicDate(unknown), 'No date');
  const inferred: AcademicDate = { date: '2026-12-01', timestamp: null, timezone: 'UTC', precision: 'date', evidenceStatus: 'inferred' };
  assert.equal(formatAcademicDate(inferred), '2026-12-01 (inferred)');
});

test('suggested practice never reads as exam', () => {
  const practice: LessonRequestView = { lessonRequestId: 'x', title: 't', learningGoal: 'g', importance: 'optional', evidenceStatus: 'suggested_practice', examScopeStatus: 'explicit', suggestedFormats: [], targetDurationSeconds: 40 };
  assert.equal(lessonExamLabel(practice), 'Suggested practice');
  const onExam: LessonRequestView = { ...practice, evidenceStatus: 'explicit', examScopeStatus: 'explicit' };
  assert.equal(lessonExamLabel(onExam), 'On the exam');
});

test('corrections: a confirmed date is marked user_confirmed, no-ops dropped', () => {
  const original = [{ assessmentId: 'a1', date: null, scopeStatus: 'unknown' }, { assessmentId: 'a2', date: '2026-10-14', scopeStatus: 'explicit' }];
  const out = buildCorrections(original, { a1: { date: '2026-11-19' }, a2: { date: '2026-10-14' } });
  assert.equal(out.length, 1);
  assert.equal(out[0].assessmentId, 'a1');
  assert.equal(out[0].date, '2026-11-19');
  assert.equal(out[0].scopeStatus, 'user_confirmed');
});

test('date input validation rejects garbage, allows empty (clear)', () => {
  assert.equal(isValidDateInput('2026-11-19'), true);
  assert.equal(isValidDateInput(''), true);
  assert.equal(isValidDateInput('next friday'), false);
  assert.equal(isValidDateInput('2026-13-40'), false);
});

test('import status labels are human', () => {
  assert.equal(importStatusLabel('needs_review'), 'Needs review');
  assert.equal(importStatusLabel('extracting'), 'Reading syllabus');
});
