// Job list. Tabs: Today / This week / Older (posted more than 7 days ago). Scam-flagged posts are hidden.
import { CalendarDays, ChevronDown, Info, MapPin, Plus, RefreshCw, Search, SearchX, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api";
import {
  Button, Card, Chip, CompanyAvatar, Empty, ErrorText, Field, MatchLabel, Notice, PageTitle, ProgressBar, Score, SkeletonCard, StatusBadge,
  Table, Tag, Visa, formatDate, inputClass,
} from "../components/ui";
import type { Job } from "../types";
import { useFetch } from "../useFetch";

const TABS = [
  { view: "today", label: "Today" },
  { view: "week", label: "This week" },
  { view: "older", label: "Older" },
] as const;
const KEYWORDS = ["industrial", "iiot", "scada", "python", "fastapi", "angular", "react"];
const FLAGS = [["visa", "Visa sponsorship"], ["english_only", "English only"], ["remote", "Remote"], ["hybrid", "Hybrid"]] as const;

export default function Jobs() {
  const [urlParams, setUrlParams] = useSearchParams();
  const [view, setView] = useState<string>("week");
  const [q, setQ] = useState(urlParams.get("q") ?? "");
  const [onlyMatches, setOnlyMatches] = useState(true);
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [keywords, setKeywords] = useState<string[]>([]);
  const [showImport, setShowImport] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const { data: settings } = useFetch("/api/settings");
  const threshold = settings?.min_score ?? 80;

  // The header search sends ?q=… : search all dates and all scores then.
  useEffect(() => {
    const fromUrl = urlParams.get("q");
    if (fromUrl !== null) {
      setQ(fromUrl);
      if (fromUrl) { setView("all"); setOnlyMatches(false); }
    }
  }, [urlParams]);

  const params = new URLSearchParams({ view, q, sort: "score" });
  if (onlyMatches) params.set("min_score", String(threshold));
  Object.entries(flags).forEach(([k, on]) => on && params.set(k, "true"));
  keywords.forEach((k) => params.append("keyword", k));
  const { data, error, loading, reload } = useFetch<{ total: number; items: Job[] }>(`/api/jobs?${params}`);

  const toggleFlag = (k: string) => setFlags({ ...flags, [k]: !flags[k] });
  const toggleKeyword = (k: string) => setKeywords(keywords.includes(k) ? keywords.filter((x) => x !== k) : [...keywords, k]);
  const activeFilters = Number(onlyMatches) + Object.values(flags).filter(Boolean).length + keywords.length;

  // Searches in steps (≤ 50 s each) so it works on Vercel too; each step continues where the last one stopped.
  async function searchNow() {
    setSearching(true);
    const total = { found: 0, new: 0, duplicates: 0, errors: [] as string[] };
    let step = { cursor: 0, blocked: [] as string[], done: false, total: 1 };
    try {
      while (!step.done) {
        setProgress(Math.round((100 * step.cursor) / step.total));
        setMessage(`Searching all sources… ${step.cursor}/${step.total === 1 ? "?" : step.total} searches · ${total.new} new jobs so far`);
        const r = await api("/api/jobs/search-step", { body: { cursor: step.cursor, blocked: step.blocked } });
        total.found += r.found; total.new += r.new; total.duplicates += r.duplicates; total.errors.push(...r.errors);
        step = r;
        if (r.new) reload();
      }
      setMessage(`Found ${total.found} · new ${total.new} · already known ${total.duplicates}${total.errors.length ? " · " + [...new Set(total.errors)].join(", ") : ""}`);
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSearching(false);
      setProgress(null);
    }
  }

  function clearSearch() {
    setQ("");
    if (urlParams.has("q")) setUrlParams({});
  }

  return (
    <div className="space-y-5">
      <PageTitle
        title="Jobs"
        subtitle={data ? `${data.total} job${data.total === 1 ? "" : "s"} · sorted by match score` : "Jobs found at German companies, scored against your CV"}
        right={
          <>
            <Button icon={showImport ? X : Plus} onClick={() => setShowImport(!showImport)}>{showImport ? "Close" : "Import job"}</Button>
            <Button kind="primary" icon={RefreshCw} loading={searching} onClick={searchNow}>Search now</Button>
          </>
        }
      />
      {message && <Notice icon={Info}>{message}{progress !== null && <div className="mt-2"><ProgressBar value={progress} label="Search progress" /></div>}</Notice>}
      {showImport && <ImportForm onClose={() => setShowImport(false)} />}

      {/* Tabs (segmented control) */}
      <div role="tablist" aria-label="Posted" className="flex gap-1 rounded-control border border-line bg-surface p-1 shadow-card sm:inline-flex">
        {[...TABS, ...(view === "all" ? [{ view: "all", label: "All dates" }] : [])].map((t) => (
          <button key={t.view} role="tab" aria-selected={view === t.view} onClick={() => setView(t.view)}
            className={`flex-1 whitespace-nowrap rounded-[8px] px-4 py-2 text-sm font-medium transition-colors duration-150 sm:flex-none ${
              view === t.view ? "bg-primary text-white shadow-sm" : "text-muted hover:bg-canvas hover:text-ink"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Search + filters */}
      <Card>
        <div className="flex gap-2">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search title, company or city</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input className={`${inputClass} pl-9 pr-9`} placeholder="Title, company, city…" value={q} onChange={(e) => setQ(e.target.value)} />
            {q && (
              <button onClick={clearSearch} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-ink" aria-label="Clear search">
                <X className="size-4" />
              </button>
            )}
          </label>
          <button onClick={() => setShowFilters(!showFilters)} aria-expanded={showFilters}
            className="inline-flex shrink-0 items-center gap-2 rounded-control border border-line px-3 text-sm font-medium text-ink hover:bg-canvas md:hidden">
            <SlidersHorizontal className="size-4" aria-hidden /> Filters
            {activeFilters > 0 && <span className="rounded-full bg-primary px-1.5 text-xs text-white">{activeFilters}</span>}
            <ChevronDown className={`size-4 transition-transform ${showFilters ? "rotate-180" : ""}`} aria-hidden />
          </button>
        </div>
        <div className={`${showFilters ? "block" : "hidden"} mt-3 space-y-3 md:block`}>
          <div className="flex flex-wrap gap-2">
            <Chip on={onlyMatches} onClick={() => setOnlyMatches(!onlyMatches)}>Only good matches (≥ {threshold})</Chip>
            {FLAGS.map(([k, label]) => <Chip key={k} on={!!flags[k]} onClick={() => toggleFlag(k)}>{label}</Chip>)}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted">Skills:</span>
            {KEYWORDS.map((k) => <Chip key={k} on={keywords.includes(k)} onClick={() => toggleKeyword(k)}>{k}</Chip>)}
          </div>
          <p className="text-xs text-muted">
            Only genuine posts from official job boards and company careers pages; posts with scam signs are hidden.
            “Posted” is the company's publish date (or the day we found it).
          </p>
        </div>
      </Card>

      <ErrorText error={error} />
      {loading && !data ? (
        <div className="space-y-3"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
      ) : !data?.items.length ? (
        <Empty
          icon={SearchX}
          title={onlyMatches ? "No good matches here" : "No jobs here yet"}
          text={onlyMatches ? "Try another tab, or turn off “Only good matches” to see every job." : "Click “Search now” to look for new jobs, or import one you found yourself."}
          action={onlyMatches ? <Button onClick={() => setOnlyMatches(false)}>Show all jobs</Button> : <Button kind="primary" icon={RefreshCw} onClick={searchNow}>Search now</Button>}
        />
      ) : (
        <>
          {/* Phones / tablets: cards */}
          <div className="grid gap-3 sm:grid-cols-2 lg:hidden">
            {data.items.map((j) => (
              <Link key={j.id} to={`/jobs/${j.id}`}
                className="block min-w-0 rounded-card border border-line bg-surface p-4 shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lift">
                <div className="flex items-start gap-3">
                  <CompanyAvatar name={j.company} />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold leading-snug text-ink">{j.title}</div>
                    <div className="truncate text-[13px] text-muted">{j.company}</div>
                  </div>
                  <Score value={j.ats_score} />
                </div>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                  <span className="inline-flex min-w-0 items-center gap-1"><MapPin className="size-3.5 shrink-0" /><span className="truncate">{j.location ?? "Unknown"}</span></span>
                  <span className="inline-flex items-center gap-1"><CalendarDays className="size-3.5" />{formatDate(j.posted_at ?? j.discovered_at)}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {j.application_status ? <StatusBadge status={j.application_status} /> : <MatchLabel match={j.match} />}
                  <Visa status={j.visa_status} />
                  {j.updated_at && <Tag color="bg-ai-50 text-ai">Updated {formatDate(j.updated_at)}</Tag>}
                </div>
              </Link>
            ))}
          </div>

          {/* Desktop: table */}
          <div className="hidden lg:block">
            <Table head={["Score", "Job", "Company", "Location", "Sponsorship", "Posted", "Status"]}>
              {data.items.map((j) => (
                <tr key={j.id} className="transition-colors hover:bg-canvas">
                  <td className="px-4 py-3"><Score value={j.ats_score} /></td>
                  <td className="max-w-[340px] px-4 py-3">
                    <Link to={`/jobs/${j.id}`} className="font-semibold text-ink hover:text-primary">{j.title}</Link>
                    <div className="mt-1 truncate text-xs text-muted">{j.top_skills.slice(0, 4).join(" · ")}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2.5 font-medium"><CompanyAvatar name={j.company} /><span className="max-w-[160px] truncate">{j.company}</span></span>
                  </td>
                  <td className="max-w-[200px] truncate px-4 py-3 text-muted">{j.location ?? "–"}</td>
                  <td className="px-4 py-3"><Visa status={j.visa_status} /></td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">
                    {formatDate(j.posted_at ?? j.discovered_at)}
                    {j.updated_at && <div className="mt-1"><Tag color="bg-ai-50 text-ai">Updated</Tag></div>}
                  </td>
                  <td className="px-4 py-3">{j.application_status ? <StatusBadge status={j.application_status} /> : <MatchLabel match={j.match} />}</td>
                </tr>
              ))}
            </Table>
          </div>
        </>
      )}
    </div>
  );
}

function ImportForm({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: "", company: "", location: "", source: "linkedin", source_url: "", application_url: "", posted_at: "", description: "" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const field = (key: keyof typeof form) => ({ value: form[key], onChange: (e: any) => setForm({ ...form, [key]: e.target.value }) });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const body = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v || null]));
      const r = await api("/api/jobs/import", { body });
      navigate(`/jobs/${r.id}`);
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <Card title="Import a job you found" subtitle="From LinkedIn, Indeed, StepStone, XING… It is saved, de-duplicated and scored." icon={Plus}
      right={<Button kind="ghost" icon={X} title="Close" onClick={onClose} />}>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="Job title"><input required className={inputClass} {...field("title")} /></Field>
        <Field label="Company"><input required className={inputClass} {...field("company")} /></Field>
        <Field label="Location"><input className={inputClass} placeholder="Berlin, Germany" {...field("location")} /></Field>
        <Field label="Posted on"><input type="date" className={inputClass} {...field("posted_at")} /></Field>
        <Field label="Job link"><input type="url" className={inputClass} {...field("source_url")} /></Field>
        <Field label="Application link"><input type="url" className={inputClass} {...field("application_url")} /></Field>
        <div className="sm:col-span-2">
          <Field label="Full job description"><textarea required minLength={50} rows={8} className={inputClass} {...field("description")} /></Field>
        </div>
        <div className="space-y-3 sm:col-span-2">
          <ErrorText error={error} />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" kind="primary" loading={saving}>Save and score</Button>
            <Button onClick={onClose}>Cancel</Button>
          </div>
        </div>
      </form>
    </Card>
  );
}
