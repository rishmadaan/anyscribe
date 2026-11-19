import { useEffect, useState } from "react";
import { getLocalRegistry } from "../api/client";

let cache: Record<string, string> | null = null;

/** Local model id -> display name ("parakeet-v3" -> "Parakeet v3"), from the
 * registry; ids pass through until it loads. */
export function useLocalModelNames(): (id: string) => string {
  const [names, setNames] = useState<Record<string, string>>(cache ?? {});
  useEffect(() => {
    if (cache) return;
    getLocalRegistry()
      .then((r) => {
        cache = Object.fromEntries(
          Object.entries(r.specs).map(([id, s]) => [id, s.display_name])
        );
        setNames(cache);
      })
      .catch(() => undefined);
  }, []);
  return (id: string) => names[id] ?? id;
}
