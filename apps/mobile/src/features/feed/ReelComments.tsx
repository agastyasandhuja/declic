import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { ApiClient } from '../../lib/api/client';
import { Button } from '../../components/Button';
import { theme } from '../../theme';
import { FeedSheet } from './FeedControls';

import { parseCommentsPage, type Comment } from './commentsData';

export function ReelComments({ open, videoId, enabled, api, onClose }: { open: boolean; videoId: string | null; enabled: boolean; api: ApiClient; onClose(): void }) {
  const [items, setItems] = useState<Comment[]>([]); const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false); const [unavailable, setUnavailable] = useState(false); const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null); const current = useRef({ open, videoId }); current.current = { open, videoId };
  const pending = useRef(false);
  async function load(next: string | null = null) {
    if (!open || !videoId || !enabled || pending.current) return;
    const controller = new AbortController(); abort.current = controller; pending.current = true; setLoading(true); setError(null);
    try {
      const query = new URLSearchParams({ limit: '20' }); if (next) query.set('cursor', next);
      const result = parseCommentsPage(await api.request(`/v1/entertainment/videos/${encodeURIComponent(videoId)}/comments?${query}`, { signal: controller.signal }));
      if (controller.signal.aborted || current.current.videoId !== videoId || !current.current.open) return;
      setUnavailable(result.availability === 'unavailable'); setCursor(result.next_cursor);
      setItems(previous => next ? [...previous, ...result.items.filter(item => !previous.some(old => old.comment_id === item.comment_id))].slice(0, 200) : result.items);
    } catch { if (!controller.signal.aborted) setError('Unable to load comments from Instagram. Try again shortly.'); }
    finally { if (abort.current === controller) { pending.current = false; setLoading(false); } }
  }
  useEffect(() => {
    abort.current?.abort(); pending.current = false; setItems([]); setCursor(null); setError(null); setUnavailable(!enabled); setLoading(false);
    if (open && videoId && enabled) void load();
    return () => { abort.current?.abort(); pending.current = false; };
  }, [open, videoId, enabled, api]);
  return <FeedSheet title="Comments" open={open} onClose={onClose}>
    <ScrollView style={{ maxHeight: 400 }} contentContainerStyle={{ gap: 20, paddingBottom: 12 }}>
      {(unavailable || !videoId) && <Text style={styles.message}>Comments aren’t available for this video.</Text>}
      {!unavailable && !loading && !error && videoId && items.length === 0 && <Text style={styles.message}>No comments to show.</Text>}
      {items.map(item => <View key={item.comment_id} style={styles.comment}><View style={styles.avatar}><Text style={styles.initial}>{(item.author.display_name || item.author.username).slice(0, 1).toUpperCase()}</Text></View><View style={{ flex: 1, gap: 5 }}><Text style={styles.author}>{item.author.display_name || `@${item.author.username}`}</Text><Text style={styles.text}>{item.text}</Text>{item.like_count > 0 && <Text style={styles.message}>{item.like_count} {item.like_count === 1 ? 'like' : 'likes'}</Text>}</View></View>)}
      {loading && <ActivityIndicator color={theme.colors.accent} />}
      {error && <><Text accessibilityRole="alert" style={styles.message}>{error}</Text><Button title="Retry comments" secondary onPress={() => void load(cursor)} /></>}
      {cursor && !loading && !error && items.length < 200 && <Button title="More comments" secondary onPress={() => void load(cursor)} />}
    </ScrollView>
    {enabled && videoId && <Text style={[styles.message, { marginTop: 16 }]}>Read-only comments from the original Reel.</Text>}
  </FeedSheet>;
}
const styles = StyleSheet.create({ comment: { flexDirection: 'row', gap: 12 }, avatar: { width: 34, height: 34, borderRadius: 17, backgroundColor: theme.colors.elevated, alignItems: 'center', justifyContent: 'center' }, initial: { fontFamily: theme.fonts.bold, color: theme.colors.accent }, author: { fontFamily: theme.fonts.bold, color: theme.colors.muted, fontSize: 12 }, text: { fontFamily: theme.fonts.body, color: theme.colors.text, fontSize: 14, lineHeight: 20 }, message: { fontFamily: theme.fonts.body, color: theme.colors.muted, fontSize: 12, lineHeight: 18 } });
