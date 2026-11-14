import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';

const clamp = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => { x = clamp(x); return x * x * (3 - 2 * x); };
const mix = (a: number, b: number, p: number) => a + (b - a) * p;
const mint = '#b8f7cb', coral = '#ff8d87', cyan = '#64c9ce', ink = '#07151a';
export const BIOLOGY_MODES = new Set([
  'enzyme_hook', 'enzyme_fit', 'enzyme_reaction', 'enzyme_reuse',
  'enzyme_compete', 'enzyme_concentration', 'enzyme_denature',
]);

// A schematic cleavage reaction, not an atomistic simulation. Consistent shapes
// carry identity across shots; position, scale and causal action carry the story.
const Label = ({x, y, children, color = '#b5c9c9'}: any) =>
  <text x={x} y={y} textAnchor="middle" fill={color} fontFamily="DejaVu Sans" fontSize={30}>{children}</text>;

const Enzyme = ({x = 0, y = 0, scale = 1, fit = 0, damage = 0}: any) => {
  const mouth = 70 - fit * 10;
  const d = clamp(damage);
  // Denaturation progressively closes and deforms the binding pocket. The
  // protein also spreads out: a different physical state, not another blocker.
  const path = `M${-mouth} ${-170 + d * 130}
    C${-190 - d * 50} ${-220 + d * 120} ${-295 - d * 25} -65 ${-225 - d * 50} 85
    C-275 ${190 - d * 20} -125 ${255 - d * 75} -10 ${200 - d * 40}
    C120 ${275 - d * 85} 260 185 ${240 + d * 65} 60
    C300 -80 190 ${-220 + d * 140} ${mouth} ${-170 + d * 130}
    L${mouth} ${-105 + d * 65}
    Q${mouth} ${-30 - d * 10} 0 ${-30 - d * 10}
    Q${-mouth} ${-30 - d * 10} ${-mouth} ${-105 + d * 65} Z`;
  return <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <ellipse cy={185} rx={240 + d * 35} ry={40} fill="#000" opacity=".22"/>
    <path d={path} fill="url(#bio-protein)" stroke={cyan} strokeWidth={3} />
    <path d={`M-195 -55 C-250 90 -160 155 -80 132 S120 193 185 85 M-172 -93 C-135 -123 -115 -90 -108 -10 C-100 68 -10 91 50 78 C125 64 159 -5 159 -82`}
      fill="none" stroke="#b9f0e7" strokeWidth={19} strokeLinecap="round" opacity={.11 * (1 - d)} />
    <path d={`M-195 0 C-135 ${100 - d * 100} -50 ${-80 + d * 100} 15 75 S150 142 205 25`}
      fill="none" stroke="#94d8d9" strokeWidth={5 + d * 5} strokeLinecap="round" opacity={.3} />
    <path d={`M${-mouth} ${-164 + d * 124} V${-105 + d * 65} Q${-mouth} ${-30 - d * 10} 0 ${-30 - d * 10} Q${mouth} ${-30 - d * 10} ${mouth} ${-105 + d * 65} V${-164 + d * 124}`}
      fill="none" stroke="#c1fff2" strokeWidth={4} opacity={.9 * (1 - d)} />
  </g>;
};

const Substrate = ({x = 0, y = 0, scale = 1, split = 0, spread = 0, angle = 0, opacity = 1, fit = 0}: any) =>
  <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`} opacity={opacity}>
    {split < .99 && <path d={`M-30 ${fit * 5} L30 ${-fit * 5}`} stroke={mint} strokeWidth={17} opacity={1 - split} />}
    <circle cx={-29 - spread * 100} cy={fit * 5 - spread * 50} r={26} fill="url(#bio-substrate)" stroke={mint} strokeWidth={2.5} />
    <circle cx={29 + spread * 100} cy={-fit * 5 - spread * 50} r={26} fill="url(#bio-substrate)" stroke={mint} strokeWidth={2.5} />
    <circle cx={-37 - spread * 100} cy={-8 + fit * 5 - spread * 50} r={6} fill="#e7fff0" opacity=".5" />
    <circle cx={21 + spread * 100} cy={-8 - fit * 5 - spread * 50} r={6} fill="#e7fff0" opacity=".5" />
  </g>;

const Inhibitor = ({x = 0, y = 0, scale = 1, angle = 0, opacity = 1}: any) =>
  <g transform={`translate(${x} ${y}) rotate(${angle}) scale(${scale})`} opacity={opacity}>
    <path d="M-55 -17 Q-63 -37 -35 -43 L35 -43 Q63 -37 55 -17 L28 26 Q0 54 -28 26 Z" fill="url(#bio-inhibitor)" stroke={coral} strokeWidth={3}/>
    <path d="M-30 -19 H29" stroke="#ffd1cb" strokeWidth={6} strokeLinecap="round" opacity=".6" />
  </g>;

const Arrow = ({x1, y1, x2, y2, opacity = 1, color = '#7a9ca2'}: any) =>
  <path d={`M${x1} ${y1} L${x2} ${y2}`} stroke={color} strokeWidth={3} fill="none" markerEnd="url(#bio-arrow)" opacity={opacity}/>;

// One complete encounter: bind → react → release. Cues have long enough holds
// to inspect the cause before the outcome, without frozen lecture slides.
const Reaction = ({x, y, scale = 1, phase = 0, showSubstrate = true}: any) => {
  const bind = smooth(phase / .28), split = smooth((phase - .40) / .10);
  // Chemical separation and spatial divergence are independent. The product
  // centres remain at x=±29 until BOTH are above y=-269 (including their radii),
  // clear of the protein's highest outline at y=-220. Only then can they diverge.
  const lift = smooth((phase - .52) / .22), spread = smooth((phase - .76) / .20);
  return <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <Enzyme fit={showSubstrate ? smooth((phase - .19) / .12) * (1 - lift) : 0} />
    {showSubstrate && <Substrate x={0} y={mix(-360, -90, bind) - lift * 210}
      split={split} spread={spread} opacity={smooth(phase / .07) * (1 - smooth((phase - .93) / .07))} fit={bind} />}
  </g>;
};

export const BiologyScenes = ({shot}: {shot: any}) => {
  const t = useCurrentFrame() / 30;
  const age = Math.max(0, t - shot.start);
  const p = clamp(age / Math.max(.01, shot.end - shot.start));
  const mode = shot.space_mode;
  const bind = smooth((p - .10) / .34);
  const fitX = mix(-120, 0, smooth(bind / .45));
  const fitY = mix(-370, -90, smooth((bind - .45) / .55));
  const inhibitorExit = smooth((p - .10) / .25);
  const competitorArrival = smooth(p / .32);
  const excludedArrival = smooth(p / .44);
  const substrateArrival = smooth((p - .39) / .23);
  // Leave a clear central entry lane and a clear exit corridor below the pool.
  const substratePool = [[700, 650], [650, 550], [940, 550], [630, 700], [960, 700], [940, 620]];
  const reusePhase = p >= .08 && p < .44 ? (p - .08) / .36
    : p >= .52 && p < .88 ? (p - .52) / .36 : null;
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 44%, #102e34 0%, #07151a 52%, #03090c 100%)'}}>
    <svg viewBox="0 0 1080 1920" width="1080" height="1920">
      <defs>
        <linearGradient id="bio-protein" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#2c858d"/><stop offset=".5" stopColor="#1a535d"/><stop offset="1" stopColor="#102d38"/></linearGradient>
        <radialGradient id="bio-substrate" cx=".3" cy=".25"><stop stopColor="#d7ffdf"/><stop offset="1" stopColor="#64b38e"/></radialGradient>
        <linearGradient id="bio-inhibitor"><stop stopColor="#ffb1a1"/><stop offset="1" stopColor="#c34e66"/></linearGradient>
        <marker id="bio-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M1 1 L8 5 L1 9" fill="none" stroke="#7a9ca2" strokeWidth="1.5"/></marker>
      </defs>

      {mode === 'enzyme_hook' && <>
        {/* A visual question: the intact machine is blocked, not destroyed. */}
        <Enzyme x={540} y={970} scale={1.45}/>
        <Inhibitor x={540} y={840} scale={1.45}/>
        <Substrate x={540 + Math.sin(age * 2) * 7} y={mix(480, 690, smooth(p * 2))} scale={1.45}/>
        <path d="M455 742 H625" stroke={coral} strokeWidth={4} strokeDasharray="8 10" opacity={smooth((p - .35) * 5)}/>
      </>}

      {mode === 'enzyme_fit' && <>
        {/* The framing closes in on binding; the pocket and substrate flex. */}
        <g transform={`translate(540 965) scale(${1.30 + smooth(p) * .28})`}>
          <Enzyme fit={smooth((p - .40) * 4)}/>
          <Substrate x={fitX} y={fitY} angle={mix(-25, 0, smooth(bind / .45))} fit={smooth((p - .4) * 4)}/>
          <g opacity={1 - smooth(bind / .45)}>
            <Label x={fitX} y={fitY - 75} color={mint}>substrate</Label>
          </g>
        </g>
      </>}

      {mode === 'enzyme_reaction' && <>
        {/* Different angle/scale reveals the bond separating, then products exit. */}
        <g transform="translate(540 955) rotate(-12)">
          <Reaction x={0} y={0} scale={1.5} phase={.27 + p * .73}/>
        </g>
      </>}

      {mode === 'enzyme_reuse' && <>
        {/* Two complete encounters use the same pocket-safe reaction path.
            Empty intervals show the enzyme reset, with no stuck products. */}
        <Reaction x={540} y={1020} scale={1.18} phase={reusePhase ?? 0} showSubstrate={reusePhase !== null}/>
      </>}

      {mode === 'enzyme_compete' && <>
        {/* Two converging paths; the coral competitor arrives first and stays. */}
        <Enzyme x={540} y={1060} scale={1.3}/>
        <Arrow x1={270} y1={420} x2={480} y2={650} opacity={.55 * (1 - smooth(p / .25))}/>
        <Arrow x1={810} y1={570} x2={600} y2={720} opacity={.55 * (1 - smooth(p / .25))}/>
        <Inhibitor x={mix(810, 540, smooth(competitorArrival / .45))}
          y={mix(500, 943, smooth((competitorArrival - .45) / .55))} scale={1.3}
          angle={mix(22, 0, smooth(competitorArrival / .45))}/>
        <Substrate x={mix(270, 540, smooth(excludedArrival / .45)) - smooth((p - .58) / .3) * 180}
          y={mix(350, 780, smooth((excludedArrival - .45) / .55)) - smooth((p - .58) / .3) * 100}
          scale={1.3} angle={mix(-20, 0, smooth(excludedArrival / .45))}/>
        <g opacity={1 - smooth(p / .25)}>
          <Label x={810} y={340} color={coral}>inhibitor</Label>
          <Label x={270} y={280} color={mint}>substrate</Label>
        </g>
      </>}

      {mode === 'enzyme_concentration' && <>
        {/* A population comparison, rather than pretending a substrate kicks an
            inhibitor off. The inhibitor dissociates BEFORE substrate binds. */}
        <path d="M540 480 V1250" stroke="#26454d" strokeWidth={2}/>
        <Label x={280} y={435}>less substrate</Label>
        <Label x={800} y={435}>more substrate</Label>
        <Enzyme x={280} y={1030} scale={.86}/>
        <Enzyme x={800} y={1030} scale={.86} fit={smooth((p - .55) * 4)}/>
        <Inhibitor x={280} y={953} scale={.86}/>
        <Substrate x={190 + Math.sin(age) * 25} y={680 + Math.cos(age) * 22} scale={.78} angle={-15}/>
        <Inhibitor x={800 + smooth((inhibitorExit - .4) / .6) * 320} y={953 - smooth(inhibitorExit / .4) * 135} scale={.86} opacity={1 - smooth((p - .26) / .12)}/>
        {Array.from({length: 6}, (_, i) => <Substrate key={i}
          x={i === 0 ? mix(700, 800, smooth(substrateArrival / .4)) : substratePool[i][0] + Math.sin(age + i) * 8}
          y={i === 0 ? mix(650, 953, smooth((substrateArrival - .4) / .6)) : substratePool[i][1] + Math.cos(age + i) * 8}
          scale={.65} angle={i === 0 ? 0 : i * 19 - 35}/>) }
        <Label x={800} y={1255} color={mint}>more binding chances</Label>
      </>}

      {mode === 'enzyme_denature' && <>
        {/* Begin with a free enzyme: heating changes the protein itself. No
            carried-over inhibitor or caption can contradict this initial state. */}
        <Enzyme x={540} y={1040} scale={1.3} damage={smooth((p - .12) / .50)}/>
        <g>
          {[0, 1, 2].map(i => <path key={i} d={`M${370 + i * 170} 620 q-32 -40 0 -80 t0 -80`} fill="none" stroke={coral} strokeWidth={5} opacity={smooth(p / .18) * .5}/>) }
          <Substrate x={540} y={mix(670, 840, smooth((p - .55) / .25))} scale={1.3} angle={Math.sin(age * 3) * 4}/>
        </g>
      </>}
    </svg>
  </AbsoluteFill>;
};
