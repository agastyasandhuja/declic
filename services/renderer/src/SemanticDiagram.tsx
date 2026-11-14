import React from 'react';
import {useCurrentFrame} from 'remotion';

export type SemanticNode = {label: string};
export type SemanticEdge = {source: number; target: number};
export type SemanticPlan = {
  mode: 'comparison' | 'sequence' | 'cause_effect';
  nodes: SemanticNode[];
  edges: SemanticEdge[];
};
const clamp = (value: number) => Math.min(1, Math.max(0, value));
const ease = (value: number) => { const t = clamp(value); return t * t * (3 - 2 * t); };
const colors = ['#9D8DF1', '#76E1D1', '#FFC97A', '#F7A5BD'];
function lines(text: string, maximum = 16): string[] {
  const result: string[] = [];
  for (const word of text.split(/\s+/)) {
    const last = result.at(-1);
    if (last && last.length + word.length + 1 <= maximum) result[result.length - 1] += ` ${word}`;
    else if (word.length <= maximum) result.push(word);
    else { result.push(word.slice(0, maximum)); result.push(word.slice(maximum)); }
  }
  return result.slice(0, 3);
}

/** Bounded, authored geometry. Labels are React text; plans cannot supply code,
 * coordinates, images, URLs, arithmetic, or hidden scene constants. Each reveal
 * changes visible relationships, then settles so the learner can read it. */
export const SemanticDiagram = ({shot}: {shot: {start: number; end: number; semantic_diagram: SemanticPlan}}) => {
  const frame = useCurrentFrame();
  const plan = shot.semantic_diagram;
  const progress = clamp((frame / 30 - shot.start) / (shot.end - shot.start));
  const count = plan.nodes.length;
  const positions = plan.nodes.map((_, i) => {
    if (plan.mode === 'comparison') return {x: count === 3 && i === 2 ? 540 : 300 + (i % 2) * 480, y: count <= 2 ? 820 : 600 + Math.floor(i / 2) * 420};
    if (plan.mode === 'cause_effect') return i === 0 ? {x: 540, y: 430} : {x: count === 2 ? 540 : count === 3 ? 270 + (i - 1) * 540 : 190 + (i - 1) * 350, y: 1010};
    return {x: 540, y: 400 + i * (840 / Math.max(1, count - 1))};
  });
  const nodeVisible = (i: number) => ease((progress - i * .13) / .2);
  const wide = plan.mode === 'sequence' || count === 2 && plan.mode === 'cause_effect';
  const width = wide ? 660 : plan.mode === 'cause_effect' && count === 4 ? 285 : 380;
  const height = plan.mode === 'sequence' ? 150 : 210;
  return <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
    <defs><radialGradient id="semantic-glow"><stop stopColor="#493A72" stopOpacity=".65"/><stop offset="1" stopColor="#080B16" stopOpacity="0"/></radialGradient></defs>
    <ellipse cx="540" cy="840" rx="530" ry="670" fill="url(#semantic-glow)"/>
    {plan.edges.map((edge, i) => {
      const from = positions[edge.source], to = positions[edge.target];
      const start = {x: from.x, y: from.y + height / 2 + 12};
      const end = {x: to.x, y: to.y - height / 2 - 16};
      const visible = ease((progress - edge.target * .13 + .04) / .2);
      const x = start.x + (end.x - start.x) * visible;
      const y = start.y + (end.y - start.y) * visible;
      const angle = Math.atan2(end.y - start.y, end.x - start.x) * 180 / Math.PI;
      return <g key={i} opacity={visible}>
        <path d={`M${start.x} ${start.y} L${x} ${y}`} fill="none" stroke={colors[edge.target]} strokeWidth="7" strokeLinecap="round"/>
        <path d="M-17 -11 L0 0 L-17 11" fill="none" stroke={colors[edge.target]} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" transform={`translate(${x} ${y}) rotate(${angle})`}/>
      </g>;
    })}
    {plan.nodes.map((node, i) => {
      const {x, y} = positions[i]; const visible = nodeVisible(i); const text = lines(node.label, width < 300 ? 12 : 16);
      const font = width < 300 ? 32 : 40;
      return <g key={i} opacity={visible} transform={`translate(${x} ${y + (1 - visible) * 28})`}>
        <rect x={-width / 2} y={-height / 2} width={width} height={height} rx="32" fill="#17192C" stroke={colors[i]} strokeWidth="4"/>
        <circle cx={-width / 2 + 26} cy={-height / 2 + 26} r="6" fill={colors[i]}/>
        <text textAnchor="middle" fill="#FFFFFF" fontFamily="DejaVu Sans,sans-serif" fontSize={font} fontWeight="700">
          {text.map((line, j) => <tspan key={j} x="0" y={(j - (text.length - 1) / 2) * (font + 12) + font * .32}>{line}</tspan>)}
        </text>
      </g>;
    })}
  </svg>;
};
