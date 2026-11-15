import { parsePlayback } from '../../contracts/validate';
import type { PlaybackSource } from '../../contracts/generated';
export type UnifiedVideo = { item_id: string; kind: 'study_video' | 'entertainment_video'; video: { video_id: string; like_count?: number | null; comment_count?: number | null; playback: PlaybackSource; title?: string; caption?: string; thumbnail_url?: string | null; source_url?: string | null; creator?: { handle?: string | null; display_name?: string | null } }; course_context?: { course_id?: string; title: string }; reason_text?: string };
export type UnifiedQuiz = { item_id: string; kind: 'quiz'; quiz: { quiz_instance_id: string; prompt: string; options: { option_id: string; text: string }[] } };
export type UnifiedItem = UnifiedVideo | UnifiedQuiz;
export interface UnifiedPage { demo_mode?: boolean; session_id: string; recommendation_revision: number; items: UnifiedItem[]; next_cursor: string | null }

const demoCourseCodes = new Map([
  ['demo_cs210', 'CS210'],
  ['demo_acc233', 'ACC233'],
  ['demo_his110', 'HIS110'],
  ['demo_math235', 'MATH235'],
]);

const semesterSuffix = /(?:\s+|\s*[-–—,:·|]\s*|(?=\())\(?(?:(?:fall|spring|summer|winter|autumn)(?:\s+semester)?[\s-]+['’]?\d{2,4}|\d{4}[\s-]+(?:fall|spring|summer|winter|autumn)|(?:FA|SP|SU|WI)\d{2})(?:\s+semester)?\)?$/i;
const courseId = /^(?:course\s*id\s*[:#-]?\s*[\w-]+|\d+(?:-\d+)*)$/i;
const courseCode = /^([A-Z]+\s*\d+[A-Z]?)(?:[-\s]+\d+)?$/;

export function studyCourseLabel(course: UnifiedVideo['course_context']): string | undefined {
  if (typeof course?.title !== 'string') return undefined;

  const cleaned = course.title
    .replace(/&(?:nbsp|#0*(?:32|160)|#x0*(?:20|a0));/gi, ' ')
    .replace(/\bCOMPSC\s*I\s*(?=\d)/gi, 'COMPSCI ')
    .trim();
  const withoutSemester = cleaned.replace(semesterSuffix, '').trimEnd();
  const suffix = withoutSemester.match(/\s*\(([^()]*)\)$/);
  const suffixText = suffix?.[1]?.trim() ?? '';
  const suffixCode = suffixText.match(courseCode)?.[1];
  const title = suffix && (suffixCode || courseId.test(suffixText))
    ? withoutSemester.slice(0, suffix.index).trimEnd()
    : withoutSemester;
  const leadingCode = title.match(/^([A-Z]+\s*\d+[A-Z]?)(?=$|[\s:–—-])/)?.[1];
  const trailingCode = title.match(/(?:\s|[:–—-])([A-Z]{2,}\s*\d{3}[A-Z]?)$/)?.[1];
  const code = leadingCode ?? trailingCode ?? demoCourseCodes.get(course.course_id ?? '') ?? suffixCode;
  return code?.replace(/^([A-Z]+)\s*(\d)/, '$1 $2');
}
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
      for (const key of ['like_count', 'comment_count'] as const) {
        const count = item.video[key];
        if (count != null && (!Number.isSafeInteger(count) || count < 0)) item.video[key] = null;
      }
      if (item.video.thumbnail_url) {
        try { const url = new URL(item.video.thumbnail_url); if (url.protocol !== 'https:' || url.username || url.password) throw new Error(); }
        catch { item.video.thumbnail_url = null; }
      }
    } else throw new Error('Unknown feed item. Please reload.');
  }
  return p;
}
export function appendUnified(previous: UnifiedItem[], incoming: UnifiedItem[]) {
  const ids = new Set(previous.map(i => i.item_id));
  return [...previous, ...incoming.filter(i => !ids.has(i.item_id))];
}
