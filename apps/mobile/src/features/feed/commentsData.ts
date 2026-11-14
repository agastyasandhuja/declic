export interface Comment { comment_id: string; text: string; author: { username: string; display_name?: string | null }; like_count: number; created_at?: string | null }
export interface CommentsPage { items: Comment[]; next_cursor: string | null; availability: 'available' | 'unavailable' }
export function parseCommentsPage(value: unknown): CommentsPage {
  const page = value as any;
  if (!page || page.schema_version !== '1' || !['available', 'unavailable'].includes(page.availability) || !Array.isArray(page.items) || page.items.length > 50 || !(page.next_cursor === null || (typeof page.next_cursor === 'string' && page.next_cursor.length <= 8192))) throw new Error('Comments are unavailable. Please retry.');
  const ids = new Set<string>();
  for (const comment of page.items) {
    if (!comment || typeof comment.comment_id !== 'string' || !comment.comment_id || comment.comment_id.length > 500 || ids.has(comment.comment_id) || typeof comment.text !== 'string' || comment.text.length > 10000 || typeof comment.author?.username !== 'string' || comment.author.username.length > 200 || !(comment.author.display_name == null || (typeof comment.author.display_name === 'string' && comment.author.display_name.length <= 200)) || !Number.isSafeInteger(comment.like_count) || comment.like_count < 0) throw new Error('Comments are unavailable. Please retry.');
    ids.add(comment.comment_id);
  }
  return page;
}

