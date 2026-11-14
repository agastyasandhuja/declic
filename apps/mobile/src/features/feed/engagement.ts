/** Unknown counts stay unknown; never turn an absent provider value into zero. */
export function compactCount(value: number | null | undefined): string | null {
  if (!Number.isSafeInteger(value) || value! < 0) return null;
  const n = value!;
  if (n < 1000) return String(n);
  const [divisor, suffix] = n < 1e6 ? [1e3, 'k'] : n < 1e9 ? [1e6, 'm'] : [1e9, 'b'];
  const scaled = Math.floor(n / divisor * 10) / 10;
  return `${scaled % 1 === 0 ? scaled.toFixed(0) : scaled.toFixed(1)}${suffix}`;
}
