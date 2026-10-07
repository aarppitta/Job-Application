// Jobs you applied to: the pipeline, application health, follow-ups. The CV and letter you sent are kept.
import { ArrowUpDown, BellRing, CalendarDays, FileText, MapPin, Search, Send } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, download } from "../api";
import {
  Chip, CompanyAvatar, Empty, ErrorText, PageTitle, Score, SkeletonCard, StatusBadge, Table, buttonClass, formatDate, inputClass,
} from "../components/ui";
import { APP_STATUS, APP_STATUSES, INTERVIEW_STAGES, REJECTION_STAGES } from "../theme";
import type { Application } from "../types";
import { useFetch } from "../useFetch";

const SORTS = { date: "Newest first", score: "Best score first", health: "Lowest health first", company: "Company A–Z" } as const;
const FILTERS: Record<string, { label: string; match: (s: string) => boolean }> = {
  active: { label: "Active", match: (s) => !["REJECTED", "WITHDRAWN", "OFFER"].includes(s) },
  interviewing: { label: "Interviewing", match: (s) => INTERVIEW_STAGES.includes(s) },
  OFFER: { label: "Offer", match: (s) => s === "OFFER" },
  REJECTED: { label: "Rejected", match: (s) => s === "REJECTED" },
};

function HealthPill({ score }: { score: number }) {
  const tone = score >= 70 ? "bg-ok-bg text-ok" : score >= 45 ? "bg-warn-bg text-warn" : "bg-bad-bg text-bad";
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${tone}`} title="Application health">{score}</span>;
}

export default function Applications() {
  const { data: apps, error, loading, reload } = useFetch<any[]>("/api/applications");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<string | null>(null);
  const [sort, setSort] = useState<keyof typeof SORTS>("date");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [askStage, setAskStage] = useState<number | null>(null);

  async function update(app: Application, body: object) {
    try {
      setSaveError(null);
      await api(`/api/applications/${app.id}`, { method: "PATCH", body });
      reload();
    } catch (e) {
      setSaveError((e as Error).message);
    }
  }

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = (apps ?? []).filter((a) =>
      (!filter || FILTERS[filter].match(a.status)) &&
      (!needle || `${a.job.title} ${a.job.company} ${a.job.location ?? ""}`.toLowerCase().includes(needle)));
    return [...list].sort((a, b) =>
      sort === "score" ? (b.score ?? 0) - (a.score ?? 0)
        : sort === "health" ? a.health.score - b.health.score
        : sort === "company" ? a.job.company.localeCompare(b.job.company)
        : b.submitted_at.localeCompare(a.submitted_at));
  }, [apps, q, filter, sort]);

  const file = (app: Application, kind: string) => `Arpita_Chaudhari_${kind}_${app.job.company.replace(/\W+/g, "_")}.docx`;
  const files = (a: Application) => (
    <span className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
      <button className="inline-flex items-center gap-1 font-medium text-primary hover:underline" onClick={() => download(`/api/applications/${a.id}/cv.docx`, file(a, "CV"))}>
        <FileText className="size-3.5" aria-hidden /> CV sent
      </button>
      <button className="inline-flex items-center gap-1 font-medium text-primary hover:underline" onClick={() => download(`/api/applications/${a.id}/cover-letter.docx`, file(a, "Cover_Letter"))}>
        <FileText className="size-3.5" aria-hidden /> Letter sent
      </button>
    </span>
  );
  const statusControl = (a: any) => (
    <div className="flex flex-col items-start gap-1.5">
      <StatusBadge status={a.status} />
      {a.status === "REJECTED" && a.rejection_stage && <span className="text-xs text-muted">at {REJECTION_STAGES[a.rejection_stage]}</span>}
      {askStage === a.id ? (
        <label className="text-xs"><span className="mb-1 block font-medium text-bad">Where did it stop?</span>
          <select autoFocus className="rounded-control border border-red-200 bg-surface px-2 py-1 text-xs" defaultValue=""
            onChange={(e) => { update(a, { status: "REJECTED", rejection_stage: e.target.value }); setAskStage(null); }}>
            <option value="" disabled>Choose stage…</option>
            {Object.entries(REJECTION_STAGES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select></label>
      ) : (
        <label className="inline-flex"><span className="sr-only">Change status of {a.job.title}</span>
          <select value={a.status} onChange={(e) => (e.target.value === "REJECTED" ? setAskStage(a.id) : update(a, { status: e.target.value }))}
            className="rounded-control border border-line bg-surface px-2 py-1 text-xs text-muted hover:border-input focus:border-primary focus:outline-none">
            {APP_STATUSES.map((s) => <option key={s} value={s}>{APP_STATUS[s].label}</option>)}
          </select></label>
      )}
    </div>
  );
  const nextStep = (a: any) => {
    const due = a.follow_ups?.find((f: any) => f.overdue) ?? a.follow_ups?.[0];
    if (due) return <span className={`inline-flex items-start gap-1 text-xs ${due.overdue ? "font-medium text-warn" : "text-muted"}`}><BellRing className="mt-0.5 size-3.5 shrink-0" />{due.text}</span>;
    if (a.health.missing[0]) return <span className="text-xs text-muted">{a.health.missing[0]}</span>;
    return <span className="text-xs text-muted">–</span>;
  };

  return (
    <div className="space-y-5">
      <PageTitle title="Applications" subtitle="Track and manage all your job applications." />
      <ErrorText error={error ?? saveError} />

      {loading && !apps ? (
        <div className="space-y-3"><SkeletonCard /><SkeletonCard /></div>
      ) : !apps?.length ? (
        <Empty icon={Send} title="No applications yet"
          text="Start applying to relevant jobs and your applications will appear here. Open a job, download the tailored CV, apply, then click “Mark as applied”."
          action={<Link to="/jobs" className={buttonClass("primary")}>Browse jobs</Link>} />
      ) : (
        <>
          <div className="space-y-3 rounded-card border border-line bg-surface p-4 shadow-card">
            <div className="flex flex-col gap-2 sm:flex-row">
              <label className="relative min-w-0 flex-1">
                <span className="sr-only">Search applications</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
                <input className={`${inputClass} pl-9`} placeholder="Search company, title or city…" value={q} onChange={(e) => setQ(e.target.value)} />
              </label>
              <label className="relative sm:w-56">
                <span className="sr-only">Sort</span>
                <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
                <select className={`${inputClass} pl-9`} value={sort} onChange={(e) => setSort(e.target.value as keyof typeof SORTS)}>
                  {Object.entries(SORTS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                </select>
              </label>
            </div>
            <div className="flex flex-wrap gap-2">
              <Chip on={filter === null} onClick={() => setFilter(null)} count={apps.length}>All</Chip>
              {Object.entries(FILTERS).map(([k, f]) => {
                const n = apps.filter((a) => f.match(a.status)).length;
                return n ? <Chip key={k} on={filter === k} onClick={() => setFilter(filter === k ? null : k)} count={n}>{f.label}</Chip> : null;
              })}
            </div>
          </div>

          {!shown.length && <Empty icon={Search} title="Nothing found" text="No application matches this search or filter." />}

          {/* Phones / tablets: cards */}
          <div className="grid gap-3 sm:grid-cols-2 lg:hidden">
            {shown.map((a) => (
              <article key={a.id} className="min-w-0 space-y-3 rounded-card border border-line bg-surface p-4 shadow-card">
                <div className="flex items-start gap-3">
                  <CompanyAvatar name={a.job.company} />
                  <div className="min-w-0 flex-1">
                    <Link to={`/jobs/${a.job.id}`} className="font-semibold leading-snug text-ink hover:text-primary">{a.job.title}</Link>
                    <div className="truncate text-[13px] text-muted">{a.job.company}</div>
                  </div>
                  <Score value={a.score} />
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                  {a.job.location && <span className="inline-flex min-w-0 items-center gap-1"><MapPin className="size-3.5 shrink-0" /><span className="truncate">{a.job.location}</span></span>}
                  <span className="inline-flex items-center gap-1"><CalendarDays className="size-3.5" />Applied {formatDate(a.submitted_at)}</span>
                  {a.cv_version && <span>{a.cv_version}</span>}
                </div>
                <div className="flex flex-wrap items-start justify-between gap-2 border-t border-line pt-3">
                  {statusControl(a)}
                  <span className="flex items-center gap-1.5 text-xs text-muted">Health <HealthPill score={a.health.score} /></span>
                </div>
                {nextStep(a)}
                {files(a)}
              </article>
            ))}
          </div>

          {/* Desktop: table */}
          {!!shown.length && (
            <div className="hidden lg:block">
              <Table head={["Company", "Job title", "Applied", "Status", "Match", "Health", "Next step", "Files"]}>
                {shown.map((a) => (
                  <tr key={a.id} className="align-top transition-colors hover:bg-canvas">
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2.5 font-semibold"><CompanyAvatar name={a.job.company} /><span className="max-w-[140px] truncate">{a.job.company}</span></span>
                    </td>
                    <td className="max-w-[260px] px-4 py-3">
                      <Link to={`/jobs/${a.job.id}`} className="font-medium text-ink hover:text-primary">{a.job.title}</Link>
                      <div className="mt-0.5 text-xs text-muted">{a.job.location ?? ""}{a.cv_version ? ` · ${a.cv_version}` : ""}</div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDate(a.submitted_at)}</td>
                    <td className="px-4 py-3">{statusControl(a)}</td>
                    <td className="px-4 py-3"><Score value={a.score} /></td>
                    <td className="px-4 py-3"><HealthPill score={a.health.score} /></td>
                    <td className="max-w-[220px] px-4 py-3">{nextStep(a)}</td>
                    <td className="px-4 py-3">{files(a)}</td>
                  </tr>
                ))}
              </Table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
