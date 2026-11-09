/** Tailnet sharing state, shared by the Settings card and the sidebar indicator.
 *
 * A change made in one is broadcast to the other with a window event, so they
 * never disagree without a page reload.
 */

import { useCallback, useEffect, useState } from "react";
import { getTailnet, setTailnet } from "../api/client";
import type { TailnetState } from "../api/client";

const EVENT = "anyscribe:tailnet";

export function useTailnet() {
  const [state, setState] = useState<TailnetState | null>(null);

  useEffect(() => {
    getTailnet()
      .then(setState)
      .catch(() => setState(null));
    const onChange = (e: Event) => setState((e as CustomEvent<TailnetState>).detail);
    window.addEventListener(EVENT, onChange);
    return () => window.removeEventListener(EVENT, onChange);
  }, []);

  const change = useCallback(async (enabled: boolean) => {
    const next = await setTailnet(enabled);
    window.dispatchEvent(new CustomEvent(EVENT, { detail: next }));
    return next;
  }, []);

  return { state, change };
}
