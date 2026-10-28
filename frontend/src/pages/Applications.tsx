// Jobs you applied to: the pipeline (table / board / calendar), application health, follow-ups, interview dates.
// The CV and letter you sent are kept.
import { ArrowUpDown, BellRing, CalendarClock, CalendarDays, Columns3, FileText, List, MapPin, Mic, Plus, Search, Send, X } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api, download } from "../api";
import {
  Button, Chip, CompanyAvatar, Empty, ErrorText, PageTitle, Score, SkeletonCard, StatusBadge, Table, buttonClass, formatDate, inputClass,
} from "../components/ui";
import { APP_STATUS, APP_STATUSES, INTERVIEW_STAGES, REJECTION_STAGES } from "../theme";
import type { Application, CalendarEvent, Interview } from "../types";
import { useFetch } from "../useFetch";

const SORTS = { date: "Newest first", score: "Best score first", health: "Lowest health first", company: "Company A–Z" } as const;
const FILTERS: Record<string, { label: string; match: (s: string) => boolean }> = {
  active: { label: "Active", match: (s) => !["REJECTED", "WITHDRAWN", "OFFER"].includes(s) },
  interviewing: { label: "Interviewing", match: (s) => INTERVIEW_STAGES.includes(s) },
  OFFER: { label: "Offer", match: (s) => s === "OFFER" },
  REJECTED: { label: "Rejected", match: (s) => s === "REJECTED" },
};

const VIEWS = [["table", "Table", List], ["board", "Board", Columns3], ["calendar", "Calendar", CalendarDays]] as const;
// Board lanes: a card dropped on a lane gets the lane's first status (Closed asks why it stopped).
const LANES = [
  { id: "applied", label: "Applied", statuses: ["APPLIED"] },
  { id: "recruiter", label: "Recruiter", statuses: ["RECRUITER_CONTACTED", "RECRUITER_REPLIED"] },
  { id: "interviewing", label: "Interviewing", statuses: INTERVIEW_STAGES },
  { id: "offer", label: "Offer", statuses: ["OFFER"] },
  { id: "closed", label: "Closed", statuses: ["REJECTED", "WITHDRAWN"] },
];
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function HealthPill({ score }: { score: number }) {
  const tone = score >= 70 ? "bg-ok-bg text-ok" : score >= 45 ? "bg-warn-bg text-warn" : "bg-bad-bg text-bad";
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${tone}`} title="Application health">{score}</span>;
}

export default function Applications() {
  const { data: apps, error, loading, reload } = useFetch<any[]>("/api/applications");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState<keyof typeof SORTS>("date");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [askStage, setAskStage] = useState<number | null>(null);
  const [view, setView] = useState<string>(() => { try { return localStorage.getItem("apps-view") ?? "table"; } catch { return "table"; } });
  const [dragging, setDragging] = useState<number | null>(null);
  const chooseView = (v: string) => { setView(v); try { localStorage.setItem("apps-view", v); } catch { /* not kept */ } };

  function dropOn(lane: (typeof LANES)[number]) {
    const app = (apps ?? []).find((a) => a.id === dragging);
    setDragging(null);
    if (!app || lane.statuses.includes(app.status)) return;
    if (lane.id === "closed") setAskStage(app.id); else update(app, { status: lane.statuses[0] });
  }

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
      (!statusFilter || a.status === statusFilter) &&
      (!needle || `${a.job.title} ${a.job.company} ${a.job.location ?? ""}`.toLowerCase().includes(needle)));
    return [...list].sort((a, b) =>
      sort === "score" ? (b.score ?? 0) - (a.score ?? 0)
        : sort === "health" ? a.health.score - b.health.score
        : sort === "company" ? a.job.company.localeCompare(b.job.company)
        : b.submitted_at.localeCompare(a.submitted_at));
  }, [apps, q, filter, statusFilter, sort]);

  const file = (app: Application, kind: string) => `${kind}_${app.job.company.replace(/\W+/g, "_")}.docx`;
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
      <PageTitle title="Applications" subtitle="Track and manage all your job applications."
        right={!!apps?.length && (
          <div role="tablist" aria-label="View" className="flex gap-1 rounded-control border border-line bg-surface p-1 shadow-card">
            {VIEWS.map(([id, label, Icon]) => (
              <button key={id} role="tab" aria-selected={view === id} onClick={() => chooseView(id)}
                className={`inline-flex items-center gap-1.5 rounded-[8px] px-3 py-1.5 text-sm font-medium transition-colors ${view === id ? "bg-primary text-white shadow-sm" : "text-muted hover:bg-canvas hover:text-ink"}`}>
                <Icon className="size-4" aria-hidden />{label}
              </button>
            ))}
          </div>
        )} />
      <ErrorText error={error ?? saveError} />

      {loading && !apps ? (
        <div className="space-y-3"><SkeletonCard /><SkeletonCard /></div>
      ) : !apps?.length ? (
        <Empty icon={Send} title="No applications yet"
          text="Start applying to relevant jobs and your applications will appear here. Open a job, download the standard CV, apply, then click “Mark as applied”."
          action={<Link to="/jobs" className={buttonClass("primary")}>Browse jobs</Link>} />
      ) : (
        <>
          {view !== "calendar" && <div className="space-y-3 rounded-card border border-line bg-surface p-4 shadow-card">
            <div className="flex flex-col gap-2 sm:flex-row">
              <label className="relative min-w-0 flex-1">
                <span className="sr-only">Search applications</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
                <input className={`${inputClass} pl-9`} placeholder="Search company, title or city…" value={q} onChange={(e) => setQ(e.target.value)} />
              </label>
              <label className="relative sm:w-56">
                <span className="sr-only">Filter by status</span>
                <select className={inputClass} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="">All statuses ({apps.length})</option>
                  {APP_STATUSES.map((s) => {
                    const n = apps.filter((a) => a.status === s).length;
                    return n ? <option key={s} value={s}>{APP_STATUS[s].label} ({n})</option> : null;
                  })}
                </select>
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
          </div>}

          {view !== "calendar" && !shown.length && <Empty icon={Search} title="Nothing found" text="No application matches this search or filter." />}

          {view === "calendar" && <Agenda />}

          {view === "board" && !!shown.length && (
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
              {LANES.map((lane) => {
                const cards = shown.filter((a) => lane.statuses.includes(a.status));
                return (
                  <section key={lane.id} aria-label={lane.label} onDragOver={(e) => e.preventDefault()} onDrop={() => dropOn(lane)}
                    className={`min-w-0 rounded-card border border-line bg-canvas p-2 ${dragging !== null ? "outline-dashed outline-1 outline-primary/40" : ""}`}>
                    <h2 className="flex items-center justify-between px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
                      {lane.label}<span className="rounded-full bg-surface px-1.5 tabular-nums">{cards.length}</span>
                    </h2>
                    <div className="space-y-2">
                      {cards.map((a) => (
                        <article key={a.id} draggable onDragStart={() => setDragging(a.id)} onDragEnd={() => setDragging(null)}
                          className="cursor-grab space-y-2 rounded-control border border-line bg-surface p-3 shadow-card active:cursor-grabbing">
                          <div className="flex items-start gap-2">
                            <div className="min-w-0 flex-1">
                              <Link to={`/jobs/${a.job.id}`} className="text-sm font-semibold leading-snug text-ink hover:text-primary">{a.job.title}</Link>
                              <div className="truncate text-xs text-muted">{a.job.company}</div>
                            </div>
                            <Score value={a.score} />
                          </div>
                          {a.interviews?.[0] && <NextInterview list={a.interviews} />}
                          {statusControl(a)}
                        </article>
                      ))}
                    </div>
                  </section>
                );
              })}
            </div>
          )}

          {/* Phones / tablets: cards */}
          {view === "table" && <div className="grid gap-3 sm:grid-cols-2 lg:hidden">
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
                <Interviews app={a} onSave={(list) => update(a, { interviews: list })} />
                {files(a)}
              </article>
            ))}
          </div>}

          {/* Desktop: table */}
          {view === "table" && !!shown.length && (
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
                    <td className="max-w-[240px] space-y-2 px-4 py-3">{nextStep(a)}<Interviews app={a} onSave={(list) => update(a, { interviews: list })} /></td>
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

function NextInterview({ list }: { list: Interview[] }) {
  const next = list.find((i) => new Date(i.at) >= new Date()) ?? list[list.length - 1];
  return <span className="inline-flex items-center gap-1 text-xs font-medium text-violet"><Mic className="size-3.5" aria-hidden />{next.kind} · {when(next.at)}</span>;
}

/** Interview dates of one application: list + add form. Saved as the whole list. */
function Interviews({ app, onSave }: { app: Application; onSave: (list: Interview[]) => Promise<void> }) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ at: "", kind: "HR screen", note: "" });
  const list = app.interviews ?? [];
  async function add(e: FormEvent) {
    e.preventDefault();
    if (!form.at) return;
    await onSave([...list, { ...form, at: new Date(form.at).toISOString() }]);
    setAdding(false);
    setForm({ at: "", kind: "HR screen", note: "" });
  }
  return (
    <div className="space-y-1">
      {list.map((i, n) => (
        <div key={n} className="flex items-start gap-1 text-xs">
          <Mic className="mt-0.5 size-3.5 shrink-0 text-violet" aria-hidden />
          <span className="min-w-0 flex-1"><b className="font-medium text-ink">{i.kind}</b> · {when(i.at)}{i.note && <span className="block text-muted">{i.note}</span>}</span>
          <button onClick={() => onSave(list.filter((_, k) => k !== n))} aria-label={`Remove ${i.kind} interview`} className="rounded p-0.5 text-slate-400 hover:text-bad"><X className="size-3" /></button>
        </div>
      ))}
      {adding ? (
        <form onSubmit={add} className="space-y-1.5 rounded-control border border-line p-2">
          <input type="datetime-local" required className={`${inputClass} h-8 py-1 text-xs`} value={form.at} onChange={(e) => setForm({ ...form, at: e.target.value })} aria-label="Interview date and time" />
          <select className={`${inputClass} h-8 py-1 text-xs`} value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })} aria-label="Interview type">
            {["HR screen", "Technical", "Take-home", "Hiring manager", "Final", "Other"].map((k) => <option key={k}>{k}</option>)}
          </select>
          <input className={`${inputClass} h-8 py-1 text-xs`} placeholder="Note (who, link…)" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} aria-label="Note" />
          <div className="flex gap-1.5"><Button type="submit" kind="primary">Save</Button><Button onClick={() => setAdding(false)}>Cancel</Button></div>
        </form>
      ) : (
        <button onClick={() => setAdding(true)} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
          <Plus className="size-3.5" aria-hidden /> Add interview date
        </button>
      )}
    </div>
  );
}

const EVENT_LOOK = {
  interview: { icon: Mic, className: "bg-violet-bg text-violet", label: "Interview" },
  follow_up: { icon: BellRing, className: "bg-info-bg text-info", label: "Follow-up" },
  deadline: { icon: CalendarClock, className: "bg-warn-bg text-warn", label: "Deadline" },
};

/** Calendar as an agenda: the next 60 days, grouped by day (interviews, follow-ups, deadlines of saved/open jobs). */
function Agenda() {
  const { data: events, error } = useFetch<CalendarEvent[]>("/api/applications/calendar?days=60");
  if (error) return <ErrorText error={error} />;
  if (!events) return <SkeletonCard />;
  if (!events.length) return <Empty icon={CalendarDays} title="Nothing planned" text="Add interview dates to your applications, or deadlines to jobs, and they show up here." />;
  const days = new Map<string, CalendarEvent[]>();
  events.forEach((e) => {
    const day = new Date(e.at).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
    days.set(day, [...(days.get(day) ?? []), e]);
  });
  return (
    <div className="space-y-4">
      {[...days].map(([day, list]) => (
        <section key={day} className="rounded-card border border-line bg-surface p-4 shadow-card">
          <h2 className="mb-2 text-sm font-semibold text-ink">{day}</h2>
          <ul className="divide-y divide-line">
            {list.map((e, n) => {
              const look = EVENT_LOOK[e.type];
              return (
                <li key={n} className="flex items-start gap-3 py-2">
                  <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${look.className}`}><look.icon className="size-3.5" aria-hidden />{look.label}</span>
                  <div className="min-w-0 flex-1 text-sm">
                    <Link to={`/jobs/${e.job_id}`} className="font-medium text-ink hover:text-primary">{e.title}</Link>
                    <div className="text-xs text-muted">{e.company}{e.type === "interview" && ` · ${new Date(e.at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`}{e.note && ` · ${e.note}`}{e.overdue && " · overdue"}</div>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
