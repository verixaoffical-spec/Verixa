/* T-096: what the Risk screens already read stays on hand, so switching views or reloading the page shows it at once.
 * Memory first, then this tab's sessionStorage (gone when the tab closes). Cleared on sign out and when the session
 * is lost, so another account in the same tab never sees it. Freshness is the caller's job: each screen re-reads in
 * the background only when its data can actually have changed (a run finished, the list is stale).
 */
const PREFIX = 'verixa:';
const mem = new Map<string, unknown>();

export function peek<T>(key: string): T | undefined {
  if (mem.has(key)) return mem.get(key) as T;
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    if (raw === null) return undefined;
    const value = JSON.parse(raw) as T;
    mem.set(key, value);
    return value;
  } catch {
    return undefined;  // storage blocked or a damaged entry: read from the server instead
  }
}

export function keep<T>(key: string, value: T): T {
  mem.set(key, value);
  try {
    sessionStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // full or blocked: memory still has it for this page
  }
  return value;
}

export function clearCache(): void {
  mem.clear();
  try {
    for (const k of Object.keys(sessionStorage)) if (k.startsWith(PREFIX)) sessionStorage.removeItem(k);
  } catch {
    // nothing stored
  }
}
