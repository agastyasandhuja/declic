import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Modal, PanResponder, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Button } from '../../components/Button';
import { theme } from '../../theme';
import { scrubTarget } from '../../lib/playback/FeedInteraction';
import type { FeedInteraction } from '../../lib/playback/FeedInteraction';

/** Center 75% opens options; the outer 12.5% on each side temporarily speeds up. */
export function FeedTouchArea({ interaction, paused, error, onToggle }: { interaction: FeedInteraction; paused: boolean; error: boolean; onToggle(): void }) {
  const held = useRef(false);
  return <View pointerEvents="box-none" style={StyleSheet.absoluteFill}>{(['left', 'center', 'right'] as const).map(zone => <Pressable key={zone}
    accessibilityRole="button" accessibilityLabel={zone === 'center' ? paused ? 'Play video. Hold for options' : 'Pause video. Hold for options' : 'Hold for double speed'}
    delayLongPress={350} onPressIn={() => { held.current = false; }}
    onLongPress={() => { held.current = true; interaction.hold(zone === 'center' ? 'center' : 'edge'); }}
    onPressOut={() => interaction.release()}
    onPress={() => { if (!held.current) onToggle(); }}
    style={[styles.touch, zone === 'center' ? { left: '12.5%', width: '75%' } : { [zone]: 0, width: '12.5%' }]}>
      {zone === 'center' && paused && !error && <View style={styles.pause}><Ionicons name="play" size={38} color="white" /></View>}
    </Pressable>)}</View>;
}

export function FeedSheet({ title, open, onClose, children }: React.PropsWithChildren<{ title: string; open: boolean; onClose(): void }>) {
  return <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
    <View style={styles.modal}><Pressable accessibilityRole="button" accessibilityLabel="Close sheet" onPress={onClose} style={StyleSheet.absoluteFill} />
      <View accessibilityViewIsModal style={styles.sheet}><View style={styles.handle} /><View style={styles.sheetHeader}><Text accessibilityRole="header" style={styles.heading}>{title}</Text><Pressable accessibilityRole="button" accessibilityLabel="Close sheet" onPress={onClose} style={styles.close}><Ionicons name="close" size={24} color={theme.colors.text} /></Pressable></View>{children}</View>
    </View>
  </Modal>;
}

export function PlaybackMenu({ open, onClose, muted, fill, captions, onMute, onFill, onCaptions, onRefresh }: { open: boolean; onClose(): void; muted: boolean; fill: boolean; captions: boolean; onMute(): void; onFill(): void; onCaptions(): void; onRefresh(): void }) {
  const action = (run: () => void) => () => { onClose(); run(); };
  return <FeedSheet title="Playback options" open={open} onClose={onClose}><View style={styles.options}>
    <Button secondary title={muted ? 'Unmute video' : 'Mute video'} onPress={action(onMute)} />
    <Button secondary title={fill ? 'Fit whole video' : 'Fill screen'} onPress={action(onFill)} />
    <Button secondary title={captions ? 'Hide captions' : 'Show captions'} onPress={action(onCaptions)} />
    <Button secondary title="Refresh feed" onPress={action(onRefresh)} />
  </View></FeedSheet>;
}

export function FeedProgress({ position, duration, disabled, onBegin, onSeek, onEnd }: { position: number; duration: number; disabled: boolean; onBegin(): void; onSeek(seconds: number): Promise<void>; onEnd(): void }) {
  const track = useRef<React.ComponentRef<typeof View>>(null); const trackLeft = useRef(0);
  const [seekError, setSeekError] = useState(false);
  const [width, setWidth] = useState(0); const [draft, setDraft] = useState<number | null>(null); const [pending, setPending] = useState(false);
  const values = useRef({ position, duration, disabled, width, onBegin, onSeek, onEnd, pending }); values.current = { position, duration, disabled, width, onBegin, onSeek, onEnd, pending };
  const target = useRef<number | null>(null); const mounted = useRef(true);
  const finish = async () => {
    const value = target.current; target.current = null;
    if (value === null) { setDraft(null); values.current.onEnd(); return; }
    setPending(true);
    try { await values.current.onSeek(value); } catch { if (mounted.current) setSeekError(true); } finally { if (mounted.current) { setPending(false); setDraft(null); } values.current.onEnd(); }
  };
  const responder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => !values.current.disabled && !values.current.pending && values.current.duration > 0,
    onMoveShouldSetPanResponder: (_event, gesture) => !values.current.disabled && !values.current.pending && Math.abs(gesture.dx) > Math.abs(gesture.dy),
    onPanResponderGrant: event => { setSeekError(false); values.current.onBegin(); target.current = scrubTarget(event.nativeEvent.pageX - trackLeft.current, values.current.width, values.current.duration); setDraft(target.current); },
    onPanResponderMove: event => { target.current = scrubTarget(event.nativeEvent.pageX - trackLeft.current, values.current.width, values.current.duration); setDraft(target.current); },
    onPanResponderRelease: () => { void finish(); },
    onPanResponderTerminationRequest: () => true,
    onPanResponderTerminate: () => { target.current = null; setDraft(null); values.current.onEnd(); },
  })).current;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; target.current = null; }; }, []);
  useEffect(() => { if (disabled && target.current !== null) { target.current = null; setDraft(null); values.current.onEnd(); } }, [disabled]);
  const nudge = (direction: number) => {
    if (disabled || pending || duration <= 0) return;
    setSeekError(false); onBegin();
    target.current = scrubTarget((position + direction * 5) / duration * width, width, duration);
    setDraft(target.current); void finish();
  };
  const value = draft ?? position; const percent = duration > 0 ? Math.max(0, Math.min(100, value / duration * 100)) : 0;
  const time = (seconds: number) => `${Math.floor(Math.max(0, seconds) / 60)}:${Math.floor(Math.max(0, seconds) % 60).toString().padStart(2, '0')}`;
  return <View style={styles.progressWrap} pointerEvents={disabled ? 'none' : 'auto'}>
    {(draft !== null || pending || seekError) && <View style={styles.timeLabel}>{pending ? <ActivityIndicator size="small" color="white" /> : null}<Text style={styles.time}>{seekError ? 'Unable to seek. Try again.' : `${time(value)} / ${time(duration)}`}</Text></View>}
    <View ref={track} {...responder.panHandlers} accessibilityRole="adjustable" accessibilityLabel="Video playback position" aria-valuemin={0} aria-valuemax={Math.max(0, duration)} aria-valuenow={Math.min(Math.max(0, value), Math.max(0, duration))} aria-valuetext={`${time(value)} of ${time(duration)}`} accessibilityValue={{ min: 0, max: Math.max(0, duration), now: Math.min(Math.max(0, value), Math.max(0, duration)), text: `${time(value)} of ${time(duration)}` }}
      accessibilityActions={[{ name: 'increment', label: 'Forward five seconds' }, { name: 'decrement', label: 'Back five seconds' }]}
      onAccessibilityAction={event => nudge(event.nativeEvent.actionName === 'increment' ? 1 : -1)}
      {...(Platform.OS === 'web' ? { tabIndex: 0, onKeyDown: (event: any) => { if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); nudge(event.key === 'ArrowRight' ? 1 : -1); } } } : {})}
      onLayout={event => { setWidth(event.nativeEvent.layout.width); track.current?.measureInWindow(x => { trackLeft.current = x; }); }} style={styles.scrubArea}>
      <View style={[styles.track, draft !== null && styles.trackActive]}><View style={[styles.fill, { width: `${percent}%` }]} /><View style={[styles.thumb, { left: `${percent}%` }, draft !== null && styles.thumbActive]} /></View>
    </View>
  </View>;
}

const styles = StyleSheet.create({
  touch: { position: 'absolute', top: 0, bottom: 0, alignItems: 'center', justifyContent: 'center' },
  pause: { height: 68, width: 68, borderRadius: 34, backgroundColor: '#09090B70', alignItems: 'center', justifyContent: 'center' },
  modal: { flex: 1, backgroundColor: '#00000066', justifyContent: 'flex-end' }, sheet: { backgroundColor: theme.colors.surface, borderTopLeftRadius: 26, borderTopRightRadius: 26, maxHeight: '75%', padding: 20, paddingBottom: 38 },
  handle: { width: 38, height: 4, borderRadius: 2, backgroundColor: '#FFFFFF55', alignSelf: 'center', marginBottom: 12 },
  sheetHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }, heading: { fontFamily: theme.fonts.bold, fontSize: 18, color: theme.colors.text }, close: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' }, options: { gap: 12 },
  progressWrap: { position: 'absolute', bottom: 0, left: 14, right: 14 }, scrubArea: { height: 30, justifyContent: 'center' }, track: { height: 3, borderRadius: 3, backgroundColor: '#FFFFFF45' }, trackActive: { height: 5 }, fill: { height: '100%', borderRadius: 3, backgroundColor: '#FFFFFF' }, thumb: { position: 'absolute', width: 8, height: 8, borderRadius: 6, top: -2.5, marginLeft: -4, backgroundColor: 'white' }, thumbActive: { width: 14, height: 14, top: -4.5, marginLeft: -7, borderRadius: 7 },
  timeLabel: { position: 'absolute', bottom: 36, alignSelf: 'center', backgroundColor: '#00000099', flexDirection: 'row', gap: 8, paddingVertical: 8, paddingHorizontal: 14, borderRadius: 16 }, time: { color: 'white', fontFamily: theme.fonts.bold, fontSize: 13 },
});
