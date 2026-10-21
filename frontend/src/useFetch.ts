import { useCallback, useEffect, useState } from "react";

import { api } from "./api";

/** Load data from the backend. `reload()` fetches again. Pass null to skip loading. */
export function useFetch<T = any>(path: string | null, refreshEverySeconds?: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      setData(await api<T>(path));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    reload();
    if (!refreshEverySeconds) return;
    // Auto-refresh only while you are looking at the page: a tab left open in the background
    // would otherwise keep asking the server (every call costs database transfer).
    const timer = setInterval(() => { if (!document.hidden) reload(); }, refreshEverySeconds * 1000);
    const onVisible = () => { if (!document.hidden) reload(); };  // catch up when you come back to the tab
    document.addEventListener("visibilitychange", onVisible);
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", onVisible); };
  }, [reload, refreshEverySeconds]);

  return { data, error, loading, reload, setData };
}
