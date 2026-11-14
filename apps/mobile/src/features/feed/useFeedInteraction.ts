import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';
import { FeedInteraction, interactionGates, type InteractionState } from '../../lib/playback/FeedInteraction';

export function useFeedInteraction(selection: string | null, active: boolean, setRate: (rate: 1 | 2) => void, onHidden?: (hidden: boolean) => void, reducedMotion = false) {
  const [state, setState] = useState<InteractionState>({ speed: 1, hidden: false, menu: false, scrubbing: false, comments: false });
  const rate = useRef(setRate); rate.current = setRate;
  const hidden = useRef(onHidden); hidden.current = onHidden;
  const alive = useRef(true);
  const reduced = useRef(reducedMotion); reduced.current = reducedMotion;
  const interaction = useMemo(() => new FeedInteraction(value => {
    if (alive.current) setState(value);
    hidden.current?.(value.hidden);
  }, value => rate.current(value), () => {
    if (!reduced.current && Platform.OS !== 'web') void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => undefined);
  }), []);
  useLayoutEffect(() => { interaction.observe(selection, active); }, [interaction, selection, active]);
  useLayoutEffect(() => { alive.current = true; return () => { alive.current = false; interaction.dispose(); }; }, [interaction]);
  return { interaction, state, ...interactionGates(state) };
}
