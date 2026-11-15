import test from 'node:test';
import assert from 'node:assert/strict';
import { appendUnified, parseUnifiedPage, studyCourseLabel } from '../src/features/feed/unified';
const quiz = { item_id: 'question', kind: 'quiz' as const, quiz: { quiz_instance_id: 'q', prompt: 'Why?', options: [{ option_id: 'a', text: 'First' }, { option_id: 'b', text: 'Second' }] } };
const page = { session_id: 'session', recommendation_revision: 1, next_cursor: null, items: [quiz] };
test('study labels show only the course code, with a space before the number', () => {
  assert.equal(
    studyCourseLabel({ title: 'Programming Methodology COMPSC I220 (174756) FA26&#x20;' }),
    'COMPSCI 220',
  );
  assert.equal(studyCourseLabel({ title: 'ACC233 — Accounting' }), 'ACC 233');
  assert.equal(studyCourseLabel({ title: 'Linear Algebra (Part 2)', course_id: 'demo_math235' }), 'MATH 235');
  assert.equal(studyCourseLabel({ title: 'Data Structures (COMPSCI 187)' }), 'COMPSCI 187');
  assert.equal(studyCourseLabel({ title: 'Data Structures (12345) FA26' }), undefined);
});
test('mixed feed rejects consumable items after a quiz boundary and duplicate occurrences', () => {
  assert.equal(parseUnifiedPage(page).items[0].kind, 'quiz');
  assert.throws(() => parseUnifiedPage({ ...page, items: [quiz, { ...quiz, item_id: 'second' }] }));
  assert.throws(() => parseUnifiedPage({ ...page, items: [quiz, quiz] }));
  assert.equal(appendUnified([quiz], [quiz]).length, 1);
});
test('mixed feed rejects insecure playback and malformed questions', () => {
  assert.throws(() => parseUnifiedPage({ ...page, items: [{ item_id: 'clip', kind: 'study_video', video: { video_id: 'v', playback: { kind: 'mp4', asset_id: 'a', url: 'http://example.com/video.mp4', expires_at: null, mime_type: 'video/mp4' } } }] }));
  assert.throws(() => parseUnifiedPage({ ...page, items: [{ ...quiz, quiz: { ...quiz.quiz, options: [{ option_id: 'a', text: 'One' }, { option_id: 'a', text: 'Two' }] } }] }));
});
