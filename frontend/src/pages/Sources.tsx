// Source health: which job sources the app reads, when each was last searched, whether it worked, and how many
// jobs it gave (open / closed). "Re-check open jobs" re-opens your best jobs' pages and hides the closed ones.
import { Activity, CircleCheck, CircleX, Info, RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";

import { api } from "../api";
import { Button, ErrorText, Notice, PageTitle, SkeletonCard, Table, Tag } from "../components/ui";
import { useFetch } from "../useFetch";

type Row = {
  source: string; enabled: boolean; companies: number | null; last_checked_at: string | null; last_ok_at: string | null;
  last_error: string | null; blocked: boolean; jobs: number; closed: number; newest_job_at: string | null;
};

const when = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "Never";

function State({ r }: { r: Row }) {
  if (!r.enabled) return <Tag>Off</Tag>;
  if (r.blocked) return <Tag color="bg-bad-bg text-bad" icon={ShieldAlert}>Blocked</Tag>;
  if (r.last_error) return <Tag color="bg-warn-bg text-warn" icon={CircleX}>Error</Tag>;
  if (!r.last_checked_at) return <Tag>Not searched yet</Tag>;
  return <Tag color="bg-ok-bg text-ok" icon={CircleCheck}>Working</Tag>;
}

export default function Sources() {
  const { data, error, reload } = useFetch<{ sources: Row[]; rechecked_jobs: number; last_recheck_at: string | null }>("/api/source-health");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function recheck() {
    setBusy(true);
    setMessage("Re-opening the pages of your best open jobs (about 2 seconds each)…");
    try {
      const r = await api("/api/jobs/recheck", { method: "POST" });
      setMessage(`Checked ${r.checked} jobs: ${r.closed.length} closed${r.closed.length ? ` (${r.closed.map((j: any) => `${j.title} · ${j.company}`).join("; ")})` : ""}` +
        `${r.unknown ? `, ${r.unknown} could not be checked (the site did not answer)` : ""}.`);
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <PageTitle title="Source health" subtitle="Where your jobs come from, when each source was last searched, and whether it worked."
        right={<Button icon={RefreshCw} loading={busy} onClick={recheck}>Re-check open jobs</Button>} />
      {message && <Notice icon={Info}>{message}</Notice>}
      <ErrorText error={error} />
      {!data ? <SkeletonCard /> : (
        <>
          <Table head={["Source", "Status", "Companies", "Last searched", "Last worked", "Jobs (closed)", "Newest job"]}>
            {data.sources.map((r) => (
              <tr key={r.source} className="align-top">
                <td className="px-4 py-3 font-medium text-ink">{r.source}</td>
                <td className="px-4 py-3">
                  <State r={r} />
                  {r.last_error && <div className="mt-1 max-w-[280px] text-xs text-muted">{r.last_error}</div>}
                </td>
                <td className="px-4 py-3 tabular-nums text-muted">{r.companies ?? "–"}</td>
                <td className="whitespace-nowrap px-4 py-3 text-muted">{when(r.last_checked_at)}</td>
                <td className="whitespace-nowrap px-4 py-3 text-muted">{when(r.last_ok_at)}</td>
                <td className="px-4 py-3 tabular-nums">{r.jobs}{r.closed ? <span className="text-muted"> ({r.closed})</span> : null}</td>
                <td className="whitespace-nowrap px-4 py-3 text-muted">{when(r.newest_job_at)}</td>
              </tr>
            ))}
          </Table>
          <p className="flex items-start gap-2 text-xs text-muted">
            <Activity className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            Only official job APIs and permitted feeds are read, one request per second. A source that answers 403 or shows a CAPTCHA is
            marked “Blocked” and never bypassed. {data.rechecked_jobs} job pages re-checked so far (last: {when(data.last_recheck_at)}); this also runs after every automation pass.
          </p>
        </>
      )}
    </div>
  );
}
