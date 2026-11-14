import { compileFromFile } from 'json-schema-to-typescript';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = new URL('../../../', import.meta.url);
const schemas = ['identity/current-user.v1', 'entertainment/feed-page.v1'];
const output = new URL('../src/contracts/generated.ts', import.meta.url);
const parts = await Promise.all(schemas.map(name => compileFromFile(
  fileURLToPath(new URL(`contracts/schemas/${name}.schema.json`, root)),
  { bannerComment: '', additionalProperties: false, unreachableDefinitions: true },
)));
const source = '// Generated from contracts/schemas by npm run contracts:generate. Do not edit.\n' + parts.join('\n');
if (process.argv.includes('--check')) {
  if (await readFile(output, 'utf8') !== source) throw new Error('Contract types are stale; run npm run contracts:generate');
  console.log('Contract types match the versioned JSON Schemas.');
} else {
  await mkdir(new URL('.', output), { recursive: true });
  await writeFile(output, source);
}
