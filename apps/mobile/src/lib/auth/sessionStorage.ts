// Metro selects .native.ts on iOS/Android. Web preview persists only in this tab.
export const sessionStorage = {
  async getItem(key: string) { return globalThis.sessionStorage?.getItem(key) ?? null; },
  async setItem(key: string, value: string) { globalThis.sessionStorage?.setItem(key, value); },
  async removeItem(key: string) { globalThis.sessionStorage?.removeItem(key); },
};
