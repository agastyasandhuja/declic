import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {validatePack} from '../validate.mjs';

function makePack(t, mutate = () => {}) {
 const root = fs.mkdtempSync(path.join(os.tmpdir(), 'semantic-pack-'));
 t.after(() => fs.rmSync(root, {recursive: true, force: true}));
 fs.mkdirSync(path.join(root, 'assets'));
 fs.writeFileSync(path.join(root, 'assets/narration.wav'), 'synthetic');
 const lesson = {format_id: 'visual_explainer', presentation: 'reference_v3', visual_strategy: 'semantic_diagram', trace_kind: 'none', frame_count: 1080, images: {}, teaching_beats: [],
  segments: Array.from({length: 6}, (_,i) => ({id: `s${i}`, start: i * 6, end: (i + 1) * 6})),
  shots: Array.from({length: 6}, (_,i) => ({segment_id: `s${i}`, kind: 'diagram', camera: i % 2 ? 'pull' : 'push', space_mode: 'galaxy', headline: '', labels: [], asset_ids: [], motion_scene: 'none', diagram_demo: 'trace', start: i * 6, end: (i + 1) * 6,
   semantic_diagram: {mode: i % 2 ? 'sequence' : 'comparison', nodes: [{label: 'Choice'}, {label: `Alternative ${i}`}], edges: i % 2 ? [{source: 0, target: 1}] : []}}))};
 mutate(lesson);
 fs.writeFileSync(path.join(root, 'lesson.json'), JSON.stringify(lesson));
 fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify({files: ['assets/narration.wav', 'lesson.json'].map(file => ({path: file, size: fs.statSync(path.join(root,file)).size, sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')}))}));
 return root;
}

test('explicit semantic diagrams work without image or scene-code capabilities', t => {
 const root = makePack(t);
 assert.equal(validatePack(root).shots.length, 6);
});
for (const [name, mutate] of Object.entries({
 'unbounded nodes': l => {l.shots[0].semantic_diagram.nodes = Array.from({length: 5}, (_,i) => ({label: `Node ${i}`}));},
 'invalid edge target': l => {l.shots[1].semantic_diagram.edges[0].target = 100;},
 'self-loop': l => {l.shots[1].semantic_diagram.edges[0].target = 0;},
 'backward edge': l => {l.shots[1].semantic_diagram.edges[0] = {source: 1, target: 0};},
 'comparison edge': l => {l.shots[0].semantic_diagram.edges.push({source: 0,target: 1});},
 'duplicate labels': l => {l.shots[0].semantic_diagram.nodes[1].label = ' choice ';},
 'unbounded label': l => {l.shots[0].semantic_diagram.nodes[0].label = 'x'.repeat(25);},
 'control characters': l => {l.shots[0].semantic_diagram.nodes[0].label = 'Label\nnewline';},
 'remote asset': l => {l.shots[0].semantic_diagram.nodes[0].url = 'https://example.test/private';},
 'model code': l => {l.shots[0].semantic_diagram.code = 'fetch("https://example.test")';},
 'specialized scene': l => {l.shots[0].motion_scene = 'ticket_loss';},
 'undeclared strategy': l => {delete l.visual_strategy;},
 'unsupported strategy': l => {l.visual_strategy = 'execute';},
 'dialogue override': l => {l.format_id = 'dialogue_gameplay';},
 'repeated slide': l => {l.shots.forEach(shot => {shot.semantic_diagram = l.shots[0].semantic_diagram;});},
})) test(`semantic pack rejects ${name}`, t => {
 assert.throws(() => validatePack(makePack(t, mutate)), /semantic|Semantic|strategy/i);
});
