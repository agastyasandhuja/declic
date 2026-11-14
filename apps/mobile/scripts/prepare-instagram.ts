import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { resolve, join } from 'node:path';
import { normalizeInstagramCatalog } from './instagram-catalog';

async function main() {
  const directory = resolve(__dirname, '../../../.local/instagram-probe');
  const page = normalizeInstagramCatalog(JSON.parse(await readFile(join(directory, 'catalog.json'), 'utf8')));
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const staged = join(directory, `feed-${randomUUID()}.json`);
  await writeFile(staged, JSON.stringify(page), { mode: 0o600 });
  await rename(staged, join(directory, 'feed.v1.json'));
  console.log(`Prepared ${page.items.length} saved Instagram clips for the local iOS preview.`);
}
void main().catch(() => { console.error('Unable to prepare the Instagram preview. Check the private catalog or run the probe again.'); process.exitCode = 1; });
