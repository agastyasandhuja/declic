/** Clear private HTTP bytes before updating their owner marker. The obsolete
 * Expo range-cache directory may never have existed; its native clear API
 * throws in that case. Delete only that known folder idempotently instead. */
export async function clearMediaCacheFiles(
  clearOwned: () => Promise<void>,
  cacheDirectory: string | null,
  deleteAsync: (uri: string, options: { idempotent: true }) => Promise<void>,
) {
  if (!cacheDirectory) throw new Error('Native cache unavailable');
  await clearOwned();
  await deleteAsync(`${cacheDirectory}expo-video-cache/`, { idempotent: true });
}
