import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { FeedInteraction, type InteractionState } from '../../lib/playback/FeedInteraction';

export function useFeedInteraction(selection: string | null, active: boolean, setRate: (rate: 1 | 2) => void, onHidden?: (hidden: boolean) => void) {
  const [state, setState] = useState<InteractionState>({ speed: 1, hidden: false, menu: false, scrubbing: false, comments: false });
  const rate = useRef(setRate); rate.current = setRate;
  const hidden = useRef(onHidden); hidden.current = onHidden;
  const alive = useRef(true);
  const interaction = useMemo(() => new FeedInteraction(value => {
    if (alive.current) setState(value);
    hidden.current?.(value.hidden);
  }, value => rate.current(value)), []);
  useLayoutEffect(() => { interaction.observe(selection, active); }, [interaction, selection, active]);
  useLayoutEffect(() => { alive.current = true; return () => { alive.current = false; interaction.dispose(); }; }, [interaction]);
  return { interaction, state, blocked: state.menu || state.comments || state.scrubbing };
}
