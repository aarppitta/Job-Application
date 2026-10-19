// Recruiter jobs: roles advertised by recruitment agencies (read from their own job pages, see sources.RECRUITER_SITES),
// scored against your CV. Apply on the recruiter's page, then "Mark as applied" saves the application in the database.
import { CalendarDays, CircleCheck, ExternalLink, Info, MapPin, RefreshCw, Search, SearchX } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import {
  Button, Chip, CompanyAvatar, Empty, ErrorText, MatchLabel, Notice, PageTitle, ProgressBar, Score, SkeletonCard, StatusBadge, Table, Tag,
  buttonClass, formatDate, inputClass,
} from "../components/ui";
import type { Job } from "../types";
import { useFetch } from "../useFetch";
import { SaveButton } from "./Jobs";

export default function RecruiterJobs() {
  const [q, setQ] = useState("");
  const [agency, setAgency] = useState("");
  const [onlyGood, setOnlyGood] = useState(false);
  const [notApplied, setNotApplied] = useState(true);
  const [sort, setSort] = useState("score");
  const [busy, setBusy] = useState<number | "search" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: settings } = useFetch("/api/settings");
  const { data: agencies } = useFetch<{ items: { name: string; jobs: number; ingestion: string; website_url: string; candidate_registration_url: string | null }[] }>("/api/agencies?sort=jobs");
  const threshold = settings?.min_score ?? 80;
  const params = new URLSearchParams({ view: "all", from_recruiters: "true", q, sort });
  if (agency) params.set("agency", agency);
  if (onlyGood) params.set("min_score", String(threshold));
  const { data, loading, reload } = useFetch<{ total: number; items: Job[] }>(`/api/jobs?${params}`);
  const items = (data?.items ?? []).filter((j) => !notApplied || !j.application_status);
  const withJobs = (agencies?.items ?? []).filter((a) => a.jobs > 0);
  const manual = (agencies?.items ?? []).filter((a) => a.ingestion === "manual" && a.jobs === 0);

  async function searchRecruiters() {
    setBusy("search"); setError(null);
    let step = { cursor: 0, blocked: [] as string[], done: false, total: 1 };
    let found = 0, fresh = 0;
    try {
      while (!step.done) {
        setProgress(Math.round((100 * step.cursor) / step.total));
        setMessage(`Reading recruiters' job pages… ${step.cursor}/${step.total === 1 ? "?" : step.total} roles · ${fresh} new jobs`);
        const r = await api("/api/jobs/search-step", { body: { cursor: step.cursor, blocked: step.blocked, only: ["recruiters"] } });
        found += r.found; fresh += r.new; step = r;
        if (r.new) reload();
      }
      setMessage(`Done: ${found} matching roles found, ${fresh} new.`);
      reload();
    } catch (e) {
      setError((e as Error).message); setMessage(null);
    } finally {
      setBusy(null); setProgress(null);
    }
  }

  async function markApplied(job: Job) {
    setBusy(job.id); setError(null);
    try {
      await api(`/api/jobs/${job.id}/applied`, { body: {} });  // saved in the database (CV, letter, score) + recruiter → Applied
      setMessage(`Saved: you applied to ${job.title} (${job.agency}). It is in Applications now.`);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const employer = (j: Job) => (j.company && j.agency && !j.company.toLowerCase().includes(j.agency.split(" ")[0].toLowerCase()) ? j.company : null);
  const actions = (j: Job) => (
    <div className="flex flex-wrap gap-2">
      {j.application_url && (
        <a href={j.application_url} target="_blank" rel="noreferrer" className={buttonClass("primary")}><ExternalLink className="size-4" aria-hidden /> Apply</a>
      )}
      {j.application_status ? <StatusBadge status={j.application_status} /> : (
        <Button kind="success" icon={CircleCheck} loading={busy === j.id} disabled={busy !== null} onClick={() => markApplied(j)}>Mark as applied</Button>
      )}
    </div>
  );

  return (
    <div className="space-y-5">
      <PageTitle title="Recruiter jobs" subtitle={data ? `${items.length} roles from recruitment agencies, scored against your CV` : "Roles advertised by recruitment agencies, scored against your CV"}
        right={<Button kind="primary" icon={RefreshCw} loading={busy === "search"} disabled={busy !== null} onClick={searchRecruiters}>Search recruiters now</Button>} />
      {message && <Notice icon={Info}>{message}{progress !== null && <div className="mt-2"><ProgressBar value={progress} label="Search progress" /></div>}</Notice>}
      <ErrorText error={error} />

      <section className="space-y-3 rounded-card border border-line bg-surface p-4 shadow-card">
        <div className="flex flex-col gap-2 md:flex-row">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search roles</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input className={`${inputClass} pl-9`} placeholder="Role, employer or city…" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <select aria-label="Recruiter" className={`${inputClass} md:w-56`} value={agency} onChange={(e) => setAgency(e.target.value)}>
            <option value="">All recruiters</option>
            {withJobs.map((a) => <option key={a.name} value={a.name}>{a.name} ({a.jobs})</option>)}
          </select>
          <select aria-label="Sort" className={`${inputClass} md:w-44`} value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="score">Best match first</option><option value="date">Newest first</option>
          </select>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip on={onlyGood} onClick={() => setOnlyGood(!onlyGood)}>Only good matches (≥ {threshold})</Chip>
          <Chip on={notApplied} onClick={() => setNotApplied(!notApplied)}>Not applied yet</Chip>
        </div>
      </section>

      {loading && !data ? (
        <div className="space-y-3"><SkeletonCard /><SkeletonCard /></div>
      ) : !items.length ? (
        <Empty icon={SearchX} title="No recruiter roles here yet" text="Click “Search recruiters now” to read the recruiters' job pages for your roles."
          action={<Button kind="primary" icon={RefreshCw} onClick={searchRecruiters}>Search recruiters now</Button>} />
      ) : (
        <>
          {/* Phones / tablets: cards */}
          <div className="grid gap-3 sm:grid-cols-2 lg:hidden">
            {items.map((j) => (
              <article key={j.id} className="min-w-0 space-y-3 rounded-card border border-line bg-surface p-4 shadow-card">
                <div className="flex items-start gap-3">
                  <CompanyAvatar name={j.agency ?? j.company} />
                  <div className="min-w-0 flex-1">
                    <Link to={`/jobs/${j.id}`} className="font-semibold leading-snug text-ink hover:text-primary">{j.title}</Link>
                    <div className="truncate text-[13px] text-muted">{employer(j) ?? "Employer not named"} · via {j.agency}</div>
                  </div>
                  <Score value={j.ats_score} />
                  <SaveButton job={j} onChange={reload} />
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                  <span className="inline-flex min-w-0 items-center gap-1"><MapPin className="size-3.5 shrink-0" /><span className="truncate">{j.location ?? "Germany"}</span></span>
                  <span className="inline-flex items-center gap-1"><CalendarDays className="size-3.5" />{formatDate(j.posted_at ?? j.discovered_at)}</span>
                </div>
                <MatchLabel match={j.match} />
                {actions(j)}
              </article>
            ))}
          </div>

          {/* Desktop: table */}
          <div className="hidden lg:block">
            <Table head={["Score", "Role", "Recruiter", "Location", "Posted", "Match", "", ""]}>
              {items.map((j) => (
                <tr key={j.id} className="align-top transition-colors hover:bg-canvas">
                  <td className="px-4 py-3"><Score value={j.ats_score} /></td>
                  <td className="max-w-[320px] px-4 py-3">
                    <Link to={`/jobs/${j.id}`} className="font-semibold text-ink hover:text-primary">{j.title}</Link>
                    <div className="mt-1 truncate text-xs text-muted">{j.top_skills.slice(0, 4).join(" · ")}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{j.agency}</div>
                    <div className="text-xs text-muted">{employer(j) ? `for ${employer(j)}` : "Employer not named"}</div>
                  </td>
                  <td className="max-w-[180px] truncate px-4 py-3 text-muted">{j.location ?? "Germany"}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDate(j.posted_at ?? j.discovered_at)}</td>
                  <td className="px-4 py-3"><MatchLabel match={j.match} /></td>
                  <td className="px-4 py-3">{actions(j)}</td>
                  <td className="px-2 py-3"><SaveButton job={j} onChange={reload} /></td>
                </tr>
              ))}
            </Table>
          </div>
        </>
      )}

      {manual.length > 0 && (
        <details className="rounded-card border border-line bg-surface p-4 text-sm shadow-card">
          <summary className="cursor-pointer font-medium text-ink">Recruiters whose job pages can't be read automatically ({manual.length})</summary>
          <p className="mt-2 text-xs text-muted">Their sites have no readable job data, block automatic reading, or did not answer. Search them yourself; paste a role you like with Jobs → Import job.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {manual.map((a) => (
              <a key={a.name} href={a.candidate_registration_url ?? a.website_url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1 text-xs text-muted hover:border-primary/40 hover:text-primary">
                {a.name} <ExternalLink className="size-3" aria-hidden />
              </a>
            ))}
          </div>
        </details>
      )}
      <p className="text-xs text-muted"><Tag>How it works</Tag> The app reads only job pages the recruiters allow (robots.txt), one per second, and never sends anything to a recruiter. Apply on their page, then click “Mark as applied”.</p>
    </div>
  );
}
