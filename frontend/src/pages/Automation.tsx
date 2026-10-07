// Start / pause / stop the 6-hour automation and watch its live log.
import { Bot, CircleAlert, History, Pause, Play, Radar, Search, Square, Target, Terminal, Copy as Duplicate } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import { Button, Card, ErrorText, Field, KpiCard, PageTitle, ProgressBar, Table, formatDate, formatTime, inputClass } from "../components/ui";
import type { Run } from "../types";
import { useFetch } from "../useFetch";

type Log = { id: number; time: string; level: string; message: string };

const RUN_LOOK: Record<string, string> = {
  RUNNING: "bg-ok-bg text-ok", PAUSED: "bg-warn-bg text-warn", FINISHED: "bg-info-bg text-info",
  STOPPED: "bg-neutral-bg text-neutral", FAILED: "bg-bad-bg text-bad",
};
const RunStatus = ({ status }: { status: string }) => (
  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${RUN_LOOK[status] ?? RUN_LOOK.STOPPED}`}>{status.charAt(0) + status.slice(1).toLowerCase()}</span>
);

export default function Automation() {
  const { data: run, reload } = useFetch<Run | null>("/api/automation/status", 3);
  const { data: settings } = useFetch("/api/settings");
  const { data: runs } = useFetch<Run[]>("/api/automation/runs", 15);
  const [config, setConfig] = useState({ max_runtime_hours: 6, min_score: 80 });
  const [logs, setLogs] = useState<Log[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const lastId = useRef(0);
  const runId = useRef<number | null>(null);
  const logBox = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (settings) setConfig((c) => ({ ...c, ...Object.fromEntries(Object.keys(c).map((k) => [k, settings[k]])) }));
  }, [settings]);

  // Ask for new log lines every 2 seconds.
  useEffect(() => {
    const timer = setInterval(async () => {
      if (run && run.id !== runId.current) {
        runId.current = run.id;
        lastId.current = 0;
        setLogs([]);
      }
      const fresh = await api<Log[]>(`/api/automation/logs?after_id=${lastId.current}`).catch(() => []);
      if (fresh.length) {
        lastId.current = fresh[fresh.length - 1].id;
        setLogs((old) => [...old, ...fresh].slice(-300));
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [run]);

  useEffect(() => {
    const box = logBox.current;
    if (box && box.scrollHeight - box.scrollTop - box.clientHeight < 80) box.scrollTop = box.scrollHeight; // follow the tail
  }, [logs]);

  async function control(action: string) {
    try {
      setError(null);
      setBusy(action);
      await api(`/api/automation/${action}`, { body: action === "start" ? config : {} });
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const active = run && ["RUNNING", "PAUSED"].includes(run.status);
  const state = run?.status === "RUNNING" ? "Running" : run?.status === "PAUSED" ? "Paused" : "Idle";
  const progress = run ? (100 * run.runtime_seconds) / (run.config.max_runtime_hours * 3600) : 0;
  const number = (key: keyof typeof config, label: string) => (
    <Field label={label}>
      <input type="number" className={inputClass} disabled={!!active} value={config[key] as number} onChange={(e) => setConfig({ ...config, [key]: Number(e.target.value) })} />
    </Field>
  );

  return (
    <div className="space-y-5">
      <PageTitle title="Automation" subtitle="Runs on the server: closing this page does not stop it. It also starts by itself every day (Settings → daily start time)." />
      <ErrorText error={error} />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card ai title="Automation status" icon={Bot} className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold ${run?.status === "RUNNING" ? "bg-ok-bg text-ok" : run?.status === "PAUSED" ? "bg-warn-bg text-warn" : "bg-neutral-bg text-neutral"}`}>
              <span className={`size-2.5 rounded-full ${run?.status === "RUNNING" ? "animate-pulse-dot bg-ok-strong" : run?.status === "PAUSED" ? "bg-amber-500" : "bg-slate-400"}`} />
              {state}
            </span>
            {run && <span className="text-sm tabular-nums text-muted">Runtime {formatTime(run.runtime_seconds)} / {formatTime(run.config.max_runtime_hours * 3600)}</span>}
          </div>
          {active && (
            <div className="mt-4">
              <div className="mb-1.5 flex justify-between text-sm"><span className="font-medium">Searching all sources</span><span className="tabular-nums text-muted">{Math.round(progress)}%</span></div>
              <ProgressBar tone="ai" value={progress} label="Automation runtime" />
            </div>
          )}
          <div className="mt-5 flex flex-wrap gap-2">
            {!active && <Button kind="ai" icon={Play} loading={busy === "start"} onClick={() => control("start")}>Start automation</Button>}
            {run?.status === "RUNNING" && <Button icon={Pause} loading={busy === "pause"} onClick={() => control("pause")}>Pause</Button>}
            {run?.status === "PAUSED" && <Button kind="ai" icon={Play} loading={busy === "resume"} onClick={() => control("resume")}>Resume</Button>}
            {active && <Button kind="danger" icon={Square} loading={busy === "stop"} onClick={() => control("stop")}>Stop</Button>}
          </div>
          {run?.summary && <p className="mt-4 rounded-control bg-ai-50 p-3 text-xs leading-relaxed text-slate-700">{run.summary}</p>}
          <p className="mt-4 text-xs text-muted">It searches your job roles on every source, saves every job and JD, and scores them, again and again until the time is up. It never applies for you.</p>
        </Card>

        <Card title="Settings for this run" icon={Target}>
          <div className="grid gap-4">
            {number("max_runtime_hours", "Max runtime (hours, ≤ 6)")}
            {number("min_score", "Minimum match score")}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <KpiCard label="New jobs found" value={run?.discovered ?? 0} icon={Search} />
        <KpiCard label="Already known" value={run?.duplicates ?? 0} icon={Duplicate} />
        <KpiCard label="Matching jobs" value={run?.qualified ?? 0} icon={Radar} tone="ai" />
        <KpiCard label="Errors / blocked" value={run?.errors ?? 0} icon={CircleAlert} tone={run?.errors ? "bad" : "primary"} />
      </div>

      <Card title="Live log" icon={Terminal} subtitle="Updates every 2 seconds">
        <div ref={logBox} className="h-72 overflow-y-auto rounded-control bg-slate-900 p-3 font-mono text-xs leading-relaxed text-slate-100 sm:h-80" aria-live="polite">
          {logs.length ? logs.map((l) => (
            <div key={l.id} className={`break-words ${l.level === "ERROR" ? "text-red-400" : l.level === "WARNING" ? "text-amber-300" : ""}`}>
              <span className="text-slate-500">{new Date(l.time).toLocaleTimeString()}</span> {l.level} {l.message}
            </div>
          )) : <span className="text-slate-400">No events yet. Start the automation to see what it does.</span>}
        </div>
      </Card>

      <Card title="Past runs" icon={History}>
        {!runs?.length ? <p className="text-sm text-muted">No runs yet.</p> : (
          <>
            <ul className="divide-y divide-line md:hidden">
              {runs.map((r) => (
                <li key={r.id} className="space-y-1 py-3 text-sm">
                  <div className="flex items-center justify-between gap-2"><span className="font-medium">{formatDate(r.started_at)}</span><RunStatus status={r.status} /></div>
                  <div className="text-muted">Found {r.discovered} · matching {r.qualified}</div>
                  {r.summary && <p className="text-xs text-muted">{r.summary}</p>}
                </li>
              ))}
            </ul>
            <div className="-mx-1 hidden md:block">
              <Table head={["Started", "Status", "Found", "Matching", "Summary"]}>
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-canvas">
                    <td className="whitespace-nowrap px-4 py-3">{new Date(r.started_at).toLocaleString()}</td>
                    <td className="px-4 py-3"><RunStatus status={r.status} /></td>
                    <td className="px-4 py-3 tabular-nums">{r.discovered}</td>
                    <td className="px-4 py-3 tabular-nums">{r.qualified}</td>
                    <td className="px-4 py-3 text-xs text-muted">{r.summary}</td>
                  </tr>
                ))}
              </Table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
