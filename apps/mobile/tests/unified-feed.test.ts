import test from 'node:test';
import assert from 'node:assert/strict';
import { appendUnified, parseUnifiedPage } from '../src/features/feed/unified';
const quiz = { item_id: 'question', kind: 'quiz' as const, quiz: { quiz_instance_id: 'q', prompt: 'Why?', options: [{ option_id: 'a', text: 'First' }, { option_id: 'b', text: 'Second' }] } };
const page = { session_id: 'session', recommendation_revision: 1, next_cursor: null, items: [quiz] };
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
