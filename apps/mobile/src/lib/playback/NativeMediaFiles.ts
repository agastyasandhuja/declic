import { clearMediaCacheFiles } from './MediaCacheCleanup';
import * as Crypto from 'expo-crypto';
import * as FS from 'expo-file-system/legacy';
import { HttpMediaCache, MEDIA_CACHE_MAX_FILE, type MediaFileEntry, type MediaFileStore } from './HttpMediaCache';
const directory = `${FS.cacheDirectory ?? ''}declic-feed-files-v1/`;
const file = (key: string) => `${directory}${key}.mp4`;
const remove = (uri: string) => FS.deleteAsync(uri, { idempotent: true });
const store: MediaFileStore = {
  key: url => Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, url), uri: file,
  exists: async key => { const value = await FS.getInfoAsync(file(key)); return value.exists && !value.isDirectory && value.size > 0; },
  async load() {
    if (!FS.cacheDirectory) throw new Error('Native cache unavailable');
    await FS.makeDirectoryAsync(directory, { intermediates: true });
    let entries: MediaFileEntry[] = [];
    try { const parsed: unknown = JSON.parse(await FS.readAsStringAsync(`${directory}index.json`)); if (Array.isArray(parsed)) entries = parsed.filter(value => value && typeof value === 'object' && typeof value.key === 'string'); } catch { /* Cold or evicted cache. */ }
    entries = entries.filter(entry => /^[a-f0-9]{64}$/.test(entry.key) && Number.isFinite(entry.bytes) && entry.bytes > 0 && entry.bytes <= MEDIA_CACHE_MAX_FILE && Number.isFinite(entry.expires) && Number.isFinite(entry.used) && (entry.url_expires === undefined || Number.isFinite(entry.url_expires)));
    const actual: MediaFileEntry[] = [];
    for (const entry of entries) {
      const info = await FS.getInfoAsync(file(entry.key));
      if (info.exists && !info.isDirectory && info.size > 0 && info.size <= MEDIA_CACHE_MAX_FILE) actual.push({ ...entry, bytes: info.size });
      else await remove(file(entry.key));
    }
    entries = actual;
    const known = new Set(entries.map(entry => `${entry.key}.mp4`));
    for (const name of await FS.readDirectoryAsync(directory)) if (name !== 'index.json' && !known.has(name)) await remove(directory + name);
    return entries;
  },
  async save(entries) { await FS.writeAsStringAsync(`${directory}index.tmp`, JSON.stringify(entries)); await remove(`${directory}index.json`); await FS.moveAsync({ from: `${directory}index.tmp`, to: `${directory}index.json` }); },
  remove: key => remove(file(key)), clear: () => remove(directory),
  async download(url, key, signal, maxBytes) {
    const temporary = `${directory}${key}.part`; let tooLarge = false;
    const task = FS.createDownloadResumable(url, temporary, { sessionType: FS.FileSystemSessionType.FOREGROUND }, progress => {
      if (progress.totalBytesWritten > maxBytes || progress.totalBytesExpectedToWrite > maxBytes) { tooLarge = true; void task.cancelAsync().catch(() => undefined); }
    });
    let cancelled = false;
    const cancel = () => { cancelled = true; void task.cancelAsync().catch(() => undefined); };
    signal.addEventListener('abort', cancel, { once: true }); const deadline = setTimeout(cancel, 30000);
    try {
      if (signal.aborted) throw new Error('Cancelled media download');
      const response = await task.downloadAsync(), info = await FS.getInfoAsync(temporary);
      const type = response?.mimeType ?? Object.entries(response?.headers ?? {}).find(([key]) => key.toLowerCase() === 'content-type')?.[1] ?? '';
      if (signal.aborted || cancelled || tooLarge || response?.status !== 200 || !info.exists || info.isDirectory || info.size <= 0 || info.size > maxBytes || !/^(video\/mp4|application\/octet-stream)(;|$)/i.test(type)) throw new Error('Incomplete media download');
      await remove(file(key)); await FS.moveAsync({ from: temporary, to: file(key) }); return info.size;
    } finally { clearTimeout(deadline); signal.removeEventListener('abort', cancel); await task.cancelAsync().catch(() => undefined); await remove(temporary).catch(() => undefined); }
  },
};
export const nativeMediaFiles = new HttpMediaCache(store);

export function clearNativeMediaFiles() {
  return clearMediaCacheFiles(() => nativeMediaFiles.clear(), FS.cacheDirectory, FS.deleteAsync);
}

export async function saveStartupDiagnostics(value: import('./StartupTrace').StartupSnapshot) {
  if (!FS.cacheDirectory) return;
  await FS.writeAsStringAsync(`${directory}startup-diagnostics.json`, JSON.stringify(value));
}
