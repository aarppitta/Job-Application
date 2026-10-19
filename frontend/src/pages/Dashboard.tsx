import {
  Bot, Briefcase, CalendarDays, Flag, ChevronRight, CircleCheck, CircleX, CalendarClock, GraduationCap, MapPin, Search, Send, Target, TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  Card, Donut, Empty, KpiCard, Notice, ProgressBar, ScoreRing, SkeletonCard, Visa, buttonClass, formatDate, formatTime,
} from "../components/ui";
import { APP_STATUSES, APP_STATUS } from "../theme";
import type { Application, Run } from "../types";
import { useFetch } from "../useFetch";

// Donut colors per application status (same meaning as the badges in theme.ts)
const STATUS_COLOR: Record<string, string> = {
  APPLIED: "#16a34a", RECRUITER_CONTACTED: "#f97316", RECRUITER_REPLIED: "#38bdf8", HR_SCREEN: "#f9a8d4", TECHNICAL: "#f472b6",
  TAKE_HOME: "#ec4899", HIRING_MANAGER: "#db2777", FINAL: "#be185d", OFFER: "#047857", REJECTED: "#dc2626", WITHDRAWN: "#9ca3af",
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function Dashboard() {
  const { data } = useFetch("/api/dashboard", 10);
  const { data: run } = useFetch<Run | null>("/api/automation/status", 5);
  const { data: profile } = useFetch("/api/profile");
  const { data: apps } = useFetch<Application[]>("/api/applications", 30);
  const { data: goal } = useFetch<any>("/api/strategy", 120);

  const counts: Record<string, number> = data?.counts ?? {};
  const count = (prefix: string) => Object.entries(counts).find(([k]) => k.startsWith(prefix))?.[1];
  const firstName = profile?.name?.split(" ")[0];
  const active = run && ["RUNNING", "PAUSED"].includes(run.status);
  const inStatus = (s: string) => apps?.filter((a) => a.status === s).length ?? 0;
  const byStatus = APP_STATUSES.filter((s) => inStatus(s) > 0 || ["APPLIED", "OFFER", "REJECTED"].includes(s))   // hide empty stages
    .map((s) => ({ label: APP_STATUS[s].label, value: inStatus(s), color: STATUS_COLOR[s] }));

  return (
    <div className="space-y-5 sm:space-y-6">
      <div>
        <span className="mb-2 block h-1.5 w-12 rounded-full bg-brand-strong" aria-hidden />
        <h1 className="text-2xl font-bold tracking-tight sm:text-[30px]">{greeting()}{firstName && <>, <span className="text-brand">{firstName}</span></>} 👋</h1>
        <p className="mt-1 text-sm text-muted">Here's what's happening with your job search.</p>
      </div>

      {goal && (
        <Link to="/strategy" className="relative flex flex-wrap items-center gap-3 overflow-hidden rounded-card border border-white bg-brand px-5 py-4 text-sm text-ink shadow-card transition hover:shadow-lift">
          <span className="pointer-events-none absolute -right-10 -top-16 size-48 rounded-full bg-white/40" aria-hidden />
          <span className="grid size-10 place-items-center rounded-control bg-white/70 text-teal-700"><Flag className="size-5" aria-hidden /></span>
          <span className="min-w-0">
            <span className="block text-base"><b className="text-xl tabular-nums">{goal.goal.days_remaining} days</b> to your job goal in Germany ({formatDate(goal.goal.goal_date)})</span>
            <span className="block text-slate-600">{goal.weekly.diagnosis[0]}</span>
          </span>
          <span className="relative ml-auto inline-flex items-center gap-1 rounded-full bg-white/80 px-3 py-1.5 font-medium text-teal-700">Strategy <ChevronRight className="size-4" /></span>
        </Link>
      )}

      {profile?.missing_facts?.length > 0 && (
        <Notice tone="warn" icon={TriangleAlert}>
          <b>Complete your profile:</b> {profile.missing_facts.join(", ")}.{" "}
          <Link to="/settings" className="font-medium text-primary underline-offset-2 hover:underline">Open Settings</Link>
        </Notice>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard label="Jobs found" value={count("Jobs found")} icon={Briefcase} hint={data && `+${count("Found today") ?? 0} today`} />
        <KpiCard label="Posted this week" value={count("Posted this week")} icon={CalendarDays} />
        <KpiCard label="Good matches to apply" value={count("Matching")} icon={Target} tone="ai" hint="not applied yet" />
        <KpiCard label="Applied" value={count("Applied")} icon={CircleCheck} tone="ok" />
        <KpiCard label="Interviews" value={count("Interview")} icon={CalendarClock} tone="violet" />
        <KpiCard label="Rejected" value={count("Rejected")} icon={CircleX} tone="bad" />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Best matches */}
        <div className="min-w-0 lg:col-span-2">
          {!data ? <SkeletonCard lines={6} /> : (
            <Card title="Best matches, not applied yet" subtitle="Ranked by your match score" icon={Target}
              right={<Link to="/jobs" className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">All jobs <ChevronRight className="size-4" /></Link>}>
              {data.top_matches?.length ? (
                <ul className="-mx-2 divide-y divide-line">
                  {data.top_matches.map((j: any) => (
                    <li key={j.id}>
                      <Link to={`/jobs/${j.id}`} className="flex items-center gap-3 rounded-control px-2 py-3 transition-colors hover:bg-canvas">
                        <ScoreRing value={j.ats_score} size={48} />
                        <span className="min-w-0 flex-1">
                          <span className="line-clamp-2 font-medium text-ink sm:line-clamp-1">{j.title}</span>
                          <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted">
                            <span className="truncate">{j.company}</span>
                            {j.location && <span className="inline-flex min-w-0 items-center gap-1"><MapPin className="size-3.5 shrink-0" /><span className="truncate">{j.location}</span></span>}
                          </span>
                          <span className="mt-1.5 block sm:hidden"><Visa status={j.visa_status} /></span>
                        </span>
                        <span className="hidden sm:block"><Visa status={j.visa_status} /></span>
                        <ChevronRight className="size-4 shrink-0 text-slate-400" aria-hidden />
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty icon={Search} title="No matching jobs yet" text="Start the automation or search now. Jobs that fit your CV will show up here."
                  action={<Link to="/jobs" className={buttonClass("primary")}>Find jobs</Link>} />
              )}
            </Card>
          )}
        </div>

        <div className="min-w-0 space-y-5">
          {/* Automation */}
          <Card ai title="Automation" icon={Bot}
            right={<Link to="/automation" className="inline-flex items-center gap-1 text-sm font-medium text-ai hover:underline">Open <ChevronRight className="size-4" /></Link>}>
            <div className="flex items-center gap-2">
              <span className={`size-2.5 rounded-full ${run?.status === "RUNNING" ? "animate-pulse-dot bg-ok-strong" : run?.status === "PAUSED" ? "bg-amber-500" : "bg-slate-400"}`} />
              <span className="font-semibold">{run?.status === "RUNNING" ? "Running" : run?.status === "PAUSED" ? "Paused" : "Idle"}</span>
              {run && active && <span className="ml-auto text-xs tabular-nums text-muted">{formatTime(run.runtime_seconds)} / {formatTime(run.config.max_runtime_hours * 3600)}</span>}
            </div>
            {run && active && <div className="mt-3"><ProgressBar tone="ai" label="Runtime" value={(100 * run.runtime_seconds) / (run.config.max_runtime_hours * 3600)} /></div>}
            {run && (
              <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
                {[["Found", run.discovered], ["Known", run.duplicates], ["Matching", run.qualified]].map(([k, v]) => (
                  <div key={k as string} className="rounded-control bg-ai-50 px-2 py-2">
                    <dt className="text-[11px] font-medium text-muted">{k}</dt>
                    <dd className="text-lg font-bold tabular-nums text-ink">{v}</dd>
                  </div>
                ))}
              </dl>
            )}
            {run?.summary && <p className="mt-3 text-xs leading-relaxed text-muted">{run.summary}</p>}
            {!run && <p className="mt-2 text-sm text-muted">Not started yet. It searches all your sources and scores every job.</p>}
          </Card>

          {/* Pipeline */}
          <Card title="Application pipeline" icon={Send}>
            {apps === null ? <SkeletonCard lines={3} /> : apps.length ? (
              <Donut parts={byStatus} center={<span><span className="block text-xl font-bold">{apps.length}</span><span className="text-[11px] text-muted">applied</span></span>} />
            ) : (
              <p className="text-sm text-muted">No applications yet. Open a match, download the standard CV, apply, then click “Mark as applied”.</p>
            )}
          </Card>
        </div>
      </div>

      {data?.skills_to_learn?.length > 0 && (
        <Card ai title="Skills to learn" subtitle="Asked by your good and near-good matches" icon={GraduationCap}>
          <div className="flex flex-wrap gap-2">
            {data.skills_to_learn.map((s: any) => (
              <span key={s.skill} className="inline-flex items-center gap-2 rounded-full border border-ai-100 bg-ai-50 px-3 py-1 text-sm">
                <b className="font-semibold text-ai">{s.skill}</b>
                <span className="text-xs text-muted">{s.jobs} job{s.jobs > 1 ? "s" : ""}</span>
              </span>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted">Open a job to see its interview prep: topics to revise, your CV stories, and gaps.</p>
        </Card>
      )}
    </div>
  );
}
