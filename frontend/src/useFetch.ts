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
    const timer = setInterval(reload, refreshEverySeconds * 1000);
    return () => clearInterval(timer);
  }, [reload, refreshEverySeconds]);

  return { data, error, loading, reload, setData };
}
