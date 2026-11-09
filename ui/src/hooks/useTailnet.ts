/** Tailnet sharing state, shared by the Settings card and the sidebar indicator.
 *
 * A change made in one is broadcast to the other with a window event, so they
 * never disagree without a page reload.
 */

import { useCallback, useEffect, useState } from "react";
import { getTailnet, setTailnet } from "../api/client";
import type { TailnetState } from "../api/client";

const EVENT = "anyscribe:tailnet";

/** Opened from another device, through the tailnet link (switching off removes this page). */
export const REMOTE = !["127.0.0.1", "localhost", "[::1]"].includes(window.location.hostname);

export function useTailnet() {
  const [state, setState] = useState<TailnetState | null>(null);

  useEffect(() => {
    const load = () =>
      getTailnet()
        .then(setState)
        .catch(() => setState(null));
    load();
    const onChange = (e: Event) => setState((e as CustomEvent<TailnetState>).detail);
    window.addEventListener(EVENT, onChange);
    // The server re-checks a live share on every read, so coming back to the window is enough.
    window.addEventListener("focus", load);
    return () => {
      window.removeEventListener(EVENT, onChange);
      window.removeEventListener("focus", load);
    };
  }, []);

  const change = useCallback(async (enabled: boolean) => {
    const broadcast = (s: TailnetState) =>
      window.dispatchEvent(new CustomEvent(EVENT, { detail: s }));
    try {
      const next = await setTailnet(enabled);
      broadcast(next);
      return next;
    } catch (err) {
      // A failed switch-off has still revoked the link: show the live state, keep the error.
      await getTailnet().then(broadcast, () => {});
      throw err;
    }
  }, []);

  return { state, change };
}
