import { parsePlayback } from '../../contracts/validate';
import type { PlaybackSource } from '../../contracts/generated';
export type UnifiedVideo = { item_id: string; kind: 'study_video' | 'entertainment_video'; video: { video_id: string; playback: PlaybackSource; title?: string; caption?: string; source_url?: string | null; creator?: { handle?: string | null; display_name?: string | null } }; course_context?: { title: string }; reason_text?: string };
export type UnifiedQuiz = { item_id: string; kind: 'quiz'; quiz: { quiz_instance_id: string; prompt: string; options: { option_id: string; text: string }[] } };
export type UnifiedItem = UnifiedVideo | UnifiedQuiz;
export interface UnifiedPage { session_id: string; recommendation_revision: number; items: UnifiedItem[]; next_cursor: string | null }
export function parseUnifiedPage(value: unknown): UnifiedPage {
  const p = value as UnifiedPage;
  if (!p || typeof p.session_id !== 'string' || !Number.isInteger(p.recommendation_revision) || !Array.isArray(p.items) || p.items.length > 50 || !(p.next_cursor === null || typeof p.next_cursor === 'string')) throw new Error('Invalid feed response. Please reload.');
  const ids = new Set<string>(); let gate = false;
  for (const item of p.items) {
    if (gate || !item || typeof item.item_id !== 'string' || ids.has(item.item_id)) throw new Error('Invalid feed order. Please reload.');
    ids.add(item.item_id);
    if (item.kind === 'quiz') {
      gate = true;
      if (!item.quiz || typeof item.quiz.quiz_instance_id !== 'string' || typeof item.quiz.prompt !== 'string' || !Array.isArray(item.quiz.options) || item.quiz.options.length < 2 || item.quiz.options.length > 8 || item.quiz.options.some(o => !o || typeof o.option_id !== 'string' || typeof o.text !== 'string') || new Set(item.quiz.options.map(o => o.option_id)).size !== item.quiz.options.length) throw new Error('This question could not be loaded. Please reload.');
    } else if (item.kind === 'study_video' || item.kind === 'entertainment_video') {
      if (!item.video || typeof item.video.video_id !== 'string') throw new Error('Invalid video. Please reload.');
      parsePlayback(item.video.playback);
    } else throw new Error('Unknown feed item. Please reload.');
  }
  return p;
}
export function appendUnified(previous: UnifiedItem[], incoming: UnifiedItem[]) {
  const ids = new Set(previous.map(i => i.item_id));
  return [...previous, ...incoming.filter(i => !ids.has(i.item_id))];
}
