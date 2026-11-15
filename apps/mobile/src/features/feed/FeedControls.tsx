import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Easing, Modal, PanResponder, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { TapGesture } from '../../lib/playback/TapGesture';
import { Button } from '../../components/Button';
import { theme } from '../../theme';
import { scrubTarget } from '../../lib/playback/FeedInteraction';
import type { FeedInteraction } from '../../lib/playback/FeedInteraction';

/** One "click" burst: a bolt that pops and floats up inside an expanding accent ring. */
function ClickBurst({ x, y, tilt, reducedMotion, onDone }: { x: number; y: number; tilt: number; reducedMotion: boolean; onDone(): void }) {
  const t = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const run = Animated.timing(t, { toValue: 1, duration: reducedMotion ? 600 : 900, easing: Easing.out(Easing.quad), useNativeDriver: true });
    run.start(() => onDone()); return () => run.stop();
  }, []);
  const opacity = t.interpolate({ inputRange: [0, 0.18, 0.75, 1], outputRange: [0, 1, 1, 0] });
  const scale = reducedMotion ? 1 : t.interpolate({ inputRange: [0, 0.18, 0.35, 0.75, 1], outputRange: [0.3, 1.25, 0.95, 1, 1.1] });
  const rise = reducedMotion ? 0 : t.interpolate({ inputRange: [0, 0.35, 0.75, 1], outputRange: [0, 0, -0.2 * BOLT, -0.7 * BOLT] });
  const ringScale = t.interpolate({ inputRange: [0, 0.66, 1], outputRange: [0.3, 2.4, 2.4] });
  const ringOpacity = t.interpolate({ inputRange: [0, 0.66, 1], outputRange: [1, 0, 0] });
  return <View pointerEvents="none" style={[styles.burst, { left: x - BOLT / 2, top: y - BOLT / 2 }]}>
    {!reducedMotion && <Animated.View style={[styles.ring, { opacity: ringOpacity, transform: [{ scale: ringScale }] }]} />}
    <Animated.View style={{ opacity, transform: [{ translateY: rise }, { scale }, { rotate: `${tilt}deg` }] }}>
      <Ionicons name="flash" size={BOLT} color={theme.colors.coral} style={styles.boltGlow} />
    </Animated.View>
  </View>;
}
const BOLT = 88;

/**
 * Tap pauses, double-tap "clicks" (likes) the clip, hold speeds up or opens options.
 * Center 75% opens options on hold; the outer 12.5% on each side temporarily speeds up.
 */
export function FeedTouchArea({ interaction, paused, error, onToggle, onDoubleTap, reducedMotion = false }: { interaction: FeedInteraction; paused: boolean; error: boolean; onToggle(): void; onDoubleTap?(): void; reducedMotion?: boolean }) {
  const held = useRef(false);
  const root = useRef<React.ComponentRef<typeof View>>(null); const origin = useRef({ x: 0, y: 0 });
  const [bursts, setBursts] = useState<{ id: number; x: number; y: number; tilt: number }[]>([]);
  const nextId = useRef(0);
  const handlers = useRef({ onToggle, onDoubleTap }); handlers.current = { onToggle, onDoubleTap };
  const taps = useRef<TapGesture | null>(null);
  if (!taps.current) taps.current = new TapGesture(() => handlers.current.onToggle(), (x, y) => {
    if (!handlers.current.onDoubleTap) return;
    handlers.current.onDoubleTap();
    if (Platform.OS !== 'web') void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => undefined);
    const id = ++nextId.current;
    setBursts(list => [...list.slice(-4), { id, x, y, tilt: Math.round(Math.random() * 30 - 15) }]);
  });
  useEffect(() => () => taps.current?.reset(), []);
  const measure = () => root.current?.measureInWindow((x, y) => { origin.current = { x, y }; });
  return <View ref={root} onLayout={measure} pointerEvents="box-none" style={StyleSheet.absoluteFill}>{(['left', 'center', 'right'] as const).map(zone => <Pressable key={zone}
    accessibilityRole="button" accessibilityLabel={zone === 'center' ? paused ? 'Play video. Hold for options' : 'Pause video. Hold for options' : 'Hold for double speed'}
    accessibilityHint={onDoubleTap ? 'Double-tap the video to click it' : undefined}
    delayLongPress={350} onPressIn={() => { held.current = false; measure(); }}
    onLongPress={() => { held.current = true; taps.current?.reset(); interaction.hold(zone === 'center' ? 'center' : 'edge'); }}
    onPressOut={() => interaction.release()}
    onPress={event => {
      if (held.current) return;
      if (!onDoubleTap) { onToggle(); return; }
      taps.current?.tap(event.nativeEvent.pageX - origin.current.x, event.nativeEvent.pageY - origin.current.y, Date.now());
    }}
    style={[styles.touch, zone === 'center' ? { left: '12.5%', width: '75%' } : { [zone]: 0, width: '12.5%' }]}>
      {zone === 'center' && paused && !error && <View style={styles.pause}><Ionicons name="play" size={38} color="white" /></View>}
    </Pressable>)}
    {bursts.map(burst => <ClickBurst key={burst.id} {...burst} reducedMotion={reducedMotion} onDone={() => setBursts(list => list.filter(item => item.id !== burst.id))} />)}
  </View>;
}

export function FeedSheet({ title, open, onClose, children, compact = false }: React.PropsWithChildren<{ title: string; open: boolean; onClose(): void; compact?: boolean }>) {
  return <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
    <View style={styles.modal}><Pressable accessibilityRole="button" accessibilityLabel="Close sheet" onPress={onClose} style={StyleSheet.absoluteFill} />
      <View accessibilityViewIsModal style={[styles.sheet, compact && { height: '62%', maxHeight: '62%' }]}><View style={styles.handle} /><View style={styles.sheetHeader}><Text accessibilityRole="header" style={styles.heading}>{title}</Text><Pressable accessibilityRole="button" accessibilityLabel="Close sheet" onPress={onClose} style={styles.close}><Ionicons name="close" size={24} color={theme.colors.text} /></Pressable></View>{children}</View>
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
  burst: { position: 'absolute', width: BOLT, height: BOLT, alignItems: 'center', justifyContent: 'center' },
  ring: { position: 'absolute', width: 64, height: 64, borderRadius: 32, borderWidth: 3, borderColor: theme.colors.accent },
  boltGlow: { textShadowColor: '#FF6B6B8C', textShadowOffset: { width: 0, height: 4 }, textShadowRadius: 18 },
  modal: { flex: 1, backgroundColor: '#00000066', justifyContent: 'flex-end' }, sheet: { backgroundColor: theme.colors.surface, borderTopLeftRadius: 26, borderTopRightRadius: 26, maxHeight: '75%', padding: 20, paddingBottom: 38 },
  handle: { width: 38, height: 4, borderRadius: 2, backgroundColor: '#FFFFFF55', alignSelf: 'center', marginBottom: 12 },
  sheetHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }, heading: { fontFamily: theme.fonts.bold, fontSize: 18, color: theme.colors.text }, close: { minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' }, options: { gap: 12 },
  progressWrap: { position: 'absolute', bottom: 0, left: 14, right: 14 }, scrubArea: { height: 30, justifyContent: 'center' }, track: { height: 3, borderRadius: 3, backgroundColor: '#FFFFFF45' }, trackActive: { height: 5 }, fill: { height: '100%', borderRadius: 3, backgroundColor: '#FFFFFF' }, thumb: { position: 'absolute', width: 8, height: 8, borderRadius: 6, top: -2.5, marginLeft: -4, backgroundColor: 'white' }, thumbActive: { width: 14, height: 14, top: -4.5, marginLeft: -7, borderRadius: 7 },
  timeLabel: { position: 'absolute', bottom: 36, alignSelf: 'center', backgroundColor: '#00000099', flexDirection: 'row', gap: 8, paddingVertical: 8, paddingHorizontal: 14, borderRadius: 16 }, time: { color: 'white', fontFamily: theme.fonts.bold, fontSize: 13 },
});

export function SpeedIndicator({ visible }: { visible: boolean }) {
  return visible ? <View pointerEvents="none" style={{ position: 'absolute', bottom: 24, alignSelf: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#00000099' }}><Text accessibilityLiveRegion="polite" style={{ color: 'white', fontFamily: theme.fonts.bold, fontSize: 14 }}>▶▶ 2× speed</Text></View> : null;
}
