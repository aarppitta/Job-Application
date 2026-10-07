// Germany Job Goal (January 2027): progress, conversion, this week's plan, and what the market wants.
import {
  BarChart3, BellRing, BookOpen, Briefcase, CalendarClock, Code, Flag, GraduationCap, Mail, Route, Send, Target, Timer, Trophy, TrendingUp, Users,
} from "lucide-react";
import { Link } from "react-router-dom";

import { DsaPill, HindiLinks } from "../components/intel";
import { Card, Empty, KpiCard, Notice, PageTitle, Pill, ProgressBar, SkeletonPage, formatDate } from "../components/ui";
import { REJECTION_STAGES } from "../theme";
import { useFetch } from "../useFetch";

export default function Strategy() {
  const { data: s, error } = useFetch<any>("/api/strategy", 60);
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!s) return <SkeletonPage />;
  const f = s.funnel;
  const conv = (v: number | null) => (v === null ? "–" : `${v}%`);

  return (
    <div className="space-y-5 sm:space-y-6">
      <PageTitle title="Germany Job Goal · January 2027" subtitle="Your search as a pipeline: is the strategy working, and what to do this week." />

      <section className="rounded-card border border-primary-100 bg-primary-50 p-5 shadow-card sm:p-6">
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-3">
            <span className="grid size-12 place-items-center rounded-control bg-primary text-white"><Timer className="size-6" /></span>
            <div><p className="text-3xl font-bold tabular-nums">{s.goal.days_remaining} days</p><p className="text-sm text-muted">until {formatDate(s.goal.goal_date)} · {s.goal.weeks_remaining} weeks</p></div>
          </div>
          <div className="grid flex-1 grid-cols-3 gap-3 text-center text-sm sm:max-w-md">
            {[["Application → interview", f.conversion.application_to_interview], ["Interview → final", f.conversion.interview_to_final], ["Final → offer", f.conversion.final_to_offer]].map(([k, v]) => (
              <div key={k as string} className="rounded-control bg-surface p-2.5"><p className="text-xl font-bold tabular-nums">{conv(v as number | null)}</p><p className="text-[11px] text-muted">{k}</p></div>
            ))}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <KpiCard label="Jobs analyzed" value={f.jobs_analyzed} icon={BarChart3} />
        <KpiCard label="Jobs shortlisted" value={f.jobs_shortlisted} icon={Target} tone="ai" />
        <KpiCard label="Applications" value={f.applications} icon={Send} tone="ok" />
        <KpiCard label="Recruiters contacted" value={f.recruiters_contacted} icon={Users} tone="warn" />
        <KpiCard label="HR responses" value={f.hr_responses} icon={Mail} />
        <KpiCard label="Interviews" value={f.interviews} icon={CalendarClock} tone="violet" />
        <KpiCard label="Technical rounds" value={f.technical_rounds} icon={Code} tone="violet" />
        <KpiCard label="Final rounds" value={f.final_rounds} icon={Flag} tone="violet" />
        <KpiCard label="Offers" value={f.offers} icon={Trophy} tone="offer" />
        <KpiCard label="Rejected" value={f.rejected} icon={TrendingUp} tone="bad" />
      </div>

      {s.follow_ups_due.length > 0 && (
        <Card title="Follow-ups due" icon={BellRing}>
          <ul className="divide-y divide-line text-sm">{s.follow_ups_due.map((x: any) => (
            <li key={x.job_id + x.text} className="flex flex-wrap justify-between gap-2 py-2"><Link to={`/jobs/${x.job_id}`} className="font-medium hover:text-primary">{x.job}</Link><span className="text-warn">{x.text}</span></li>
          ))}</ul>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Card ai title="This week's strategy" subtitle="Adjusts to your real results" icon={Route}>
          {s.weekly.diagnosis.map((d: string) => <Notice key={d} tone="ai">{d}</Notice>)}
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            {[["Applications", s.weekly.targets.applications], ["Recruiter outreach", s.weekly.targets.recruiter_outreach],
              ["DSA problems", s.weekly.targets.dsa_problems], ["Interview practice", `${s.weekly.targets.interview_practice_hours} h`]].map(([k, v]) => (
              <div key={k as string} className="rounded-control border border-line p-3"><dt className="text-xs text-muted">{k}</dt><dd className="font-semibold">{v}</dd></div>
            ))}
          </dl>
          <h3 className="mb-2 mt-4 text-sm font-semibold">Study plan this week</h3>
          <ul className="space-y-2 text-sm">{s.weekly.study_plan.map((p: any) => (
            <li key={p.skill} className="flex items-center justify-between gap-3"><span><b>{p.skill}</b> <span className="text-xs text-muted">· {p.why}</span></span><Pill className="bg-ai-50 text-ai">{p.hours} h</Pill></li>
          ))}</ul>
        </Card>
        <Card title="Learning from rejections" subtitle="Mark the stage when you set an application to Rejected" icon={GraduationCap}>
          {Object.keys(s.rejections.by_stage).length ? (
            <>
              <ul className="space-y-1.5 text-sm">{Object.entries(s.rejections.by_stage).map(([k, v]) => (
                <li key={k} className="flex justify-between"><span>{REJECTION_STAGES[k] ?? k}</span><b>{v as number}</b></li>
              ))}</ul>
              {s.rejections.lessons.length ? <div className="mt-3 space-y-2">{s.rejections.lessons.map((l: string) => <Notice key={l} tone="warn">{l}</Notice>)}</div>
                : <p className="mt-3 text-sm text-muted">Not enough rejections at one stage to see a pattern yet.</p>}
            </>
          ) : <Empty icon={GraduationCap} title="No rejections recorded" text="When an application is rejected, choose the stage. The weekly plan learns from it." />}
        </Card>
      </div>

      <Card title="What your target market asks for" subtitle={`${s.skills.jobs_analyzed} target jobs in Germany (score ≥ threshold − 25)`} icon={BarChart3}>
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <ul className="space-y-2">
            {s.skills.skills.slice(0, 15).map((r: any) => (
              <li key={r.skill} className="text-sm">
                <div className="mb-1 flex justify-between gap-2"><span className="font-medium">{r.skill} <span className="text-xs font-normal text-muted">· {r.status === "strong" ? "you have it" : r.status === "partial" ? "partial" : "missing"}</span></span><span className="tabular-nums text-muted">{r.share}%</span></div>
                <ProgressBar value={r.share} tone={r.status === "strong" ? "ok" : "primary"} label={r.skill} />
              </li>
            ))}
          </ul>
          <div className="space-y-4 text-sm">
            <div><h3 className="mb-1.5 font-semibold text-ok">Skills you already have</h3><div className="flex flex-wrap gap-1.5">{s.skills.have.map((r: any) => <Pill key={r.skill} className="bg-ok-bg text-ok">{r.skill} · {r.share}%</Pill>)}</div></div>
            <div><h3 className="mb-1.5 font-semibold text-ai">Improve next (highest learning ROI)</h3>
              <ol className="space-y-2.5">{s.skills.improve.map((r: any, i: number) => (
                <li key={r.skill}>{i + 1}. <b>{r.skill}</b> <span className="text-muted">· {r.share}% of jobs · {r.time} · ROI {r.roi}</span>
                  <HindiLinks links={r.learn_hindi} compact /></li>
              ))}</ol></div>
            {s.skills.needs_experience.length > 0 && (
              <div><h3 className="mb-1.5 font-semibold text-warn">Asked often, but needs real production experience</h3>
                <p className="text-muted">{s.skills.needs_experience.map((r: any) => `${r.skill} (${r.share}%)`).join(", ")}: don't try to learn these for this search; target roles without them.</p></div>
            )}
            <div><h3 className="mb-1.5 font-semibold text-muted">Don't spend much time on (under 8% of jobs)</h3><p className="text-muted">{s.skills.skip.map((r: any) => r.skill).join(", ") || "–"}</p></div>
          </div>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="DSA across your target companies" subtitle={`Minimum curriculum: ${s.dsa.curriculum_level} (covers ≥70% of your targets)`} icon={Code}>
          <ul className="space-y-2 text-sm">{s.dsa.by_company_type.map((r: any) => (
            <li key={r.type} className="flex flex-wrap items-center justify-between gap-2"><span>{r.type} <span className="text-muted">· {r.share}% ({r.jobs})</span></span><DsaPill level={r.level} /></li>
          ))}</ul>
          <h3 className="mb-2 mt-4 text-sm font-semibold">Prepare (~{s.dsa.curriculum.problems} problems)</h3>
          <div className="flex flex-wrap gap-1.5">{s.dsa.curriculum.required.map((t: string) => <Pill key={t} className="bg-primary-50 text-primary">{t}</Pill>)}</div>
          <div className="mt-3"><HindiLinks links={s.dsa.learn_hindi} compact /></div>
          {s.dsa.skip.length > 0 && <p className="mt-3 text-sm text-muted"><b>Skip for now:</b> {s.dsa.skip.join(", ")}. Your targets rarely need them.</p>}
        </Card>
        <Card title="Which roles fit you best" subtitle="Average score of the top 10 jobs per role family" icon={Briefcase}>
          <ul className="divide-y divide-line text-sm">{s.roles.map((r: any) => (
            <li key={r.family} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
              <span className="min-w-0"><b>{r.family}</b> <span className="text-xs text-muted">· {r.primary ? "primary" : "secondary"} · {r.jobs} jobs · {r.good} good matches</span></span>
              <span className="flex items-center gap-2"><b className="tabular-nums">{r.avg_top10}</b>
                <Pill className={r.advice === "Focus" ? "bg-ok-bg text-ok" : r.advice === "Also apply" ? "bg-info-bg text-info" : "bg-neutral-bg text-neutral"}>{r.advice}</Pill></span>
            </li>
          ))}</ul>
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted"><BookOpen className="size-3.5" /> Rankings use your own scored jobs, not general market data.</p>
        </Card>
      </div>
    </div>
  );
}
