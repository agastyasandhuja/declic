import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {build} from 'esbuild';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

test('semantic diagrams settle with bounded visible nodes and a finite directed relationship per edge', async t => {
 const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'semantic-render-'));
 t.after(async () => { delete globalThis.__semanticTestFrame; await fs.rm(dir, {recursive: true, force: true}); });
 const renderer = fileURLToPath(new URL('../', import.meta.url)), outfile = path.join(dir, 'diagram.mjs');
 await build({entryPoints: [path.join(renderer, 'src/SemanticDiagram.tsx')], bundle: true, platform: 'node', format: 'esm', outfile,
  plugins: [{name: 'frame-only-remotion', setup(builder) {
   builder.onResolve({filter: /^remotion$/}, () => ({path: 'remotion', namespace: 'test'}));
   builder.onLoad({filter: /.*/, namespace: 'test'}, () => ({contents: 'export const useCurrentFrame=()=>globalThis.__semanticTestFrame;'}));
  }}]});
 const {SemanticDiagram} = await import(pathToFileURL(outfile).href);
 for (const mode of ['comparison', 'sequence', 'cause_effect']) for (const count of [2, 3, 4]) {
  const nodes = Array.from({length: count}, (_, i) => ({label: `Concept ${i + 1}`}));
  const edges = mode === 'comparison' ? [] : nodes.slice(1).map((_, i) => ({source: mode === 'sequence' ? i : 0, target: i + 1}));
  const shot = {start: 0, end: 5, semantic_diagram: {mode, nodes, edges}};
  globalThis.__semanticTestFrame = 0;
  const beginning = renderToStaticMarkup(React.createElement(SemanticDiagram, {shot}));
  assert.ok(beginning.includes('opacity="0"'), 'Start state should precede the reveal');
  globalThis.__semanticTestFrame = 149;
  const end = renderToStaticMarkup(React.createElement(SemanticDiagram, {shot}));
  assert.ok(!/NaN|Infinity/.test(end));
  const groups = [...end.matchAll(/<g opacity="1" transform="translate\(([-\d.]+) ([-\d.]+)\)"><rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"/g)];
  assert.equal(groups.length, count);
  const boxes = groups.map(match => { const [x,y,left,top,width,height] = match.slice(1).map(Number); return {left:x+left, top:y+top, right:x+left+width, bottom:y+top+height}; });
  for (const box of boxes) {
   assert.ok(box.left >= 40 && box.right <= 1040, 'Keep nodes inside phone-safe horizontal bounds');
   assert.ok(box.top >= 290 && box.bottom <= 1350, 'Keep nodes clear of captions and navigation');
  }
  for (let i = 0; i < boxes.length; i++) for (const b of boxes.slice(i + 1)) {
   const a = boxes[i]; assert.ok(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top, 'Nodes must not overlap');
  }
  assert.equal((end.match(/stroke-linecap="round" stroke-linejoin="round"/g) || []).length, edges.length, 'Each relation has exactly one arrowhead');
 }
});
