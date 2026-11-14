import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseAcademicProfile } from '../src/features/settings/academicData';
const profile = (scheduled: object) => ({ courses: [], units: [], assessments: [{ course_id: 'course', title: 'Exam', scheduled }] });
test('academic display preserves date-only precision and never upgrades inferred dates', () => {
  assert.equal(parseAcademicProfile(profile({ precision: 'date', date: '2026-11-20', timezone: 'America/New_York', evidence_status: 'explicit' })).assessments[0].dateLabel, '2026-11-20 · America/New_York · date only');
  assert.equal(parseAcademicProfile(profile({ precision: 'date', date: '2026-11-20', evidence_status: 'inferred' })).assessments[0].dateLabel, 'Date needs confirmation');
  assert.equal(parseAcademicProfile(profile({ precision: 'datetime', timestamp: '2026-11-20T12:00:00', evidence_status: 'explicit' })).assessments[0].dateLabel, 'Date needs confirmation');
});
test('malformed academic data fails into recoverable UI rather than fabricated coursework', () => {
  assert.throws(() => parseAcademicProfile({ courses: 'invalid', units: [], assessments: [] }));
  assert.throws(() => parseAcademicProfile({ courses: [{course_id: 4}], units: [], assessments: [] }));
});
