// One job = one decision: should I apply, how strong is my match, what am I missing, who do I contact, what next?
import {
  ArrowLeft, Brain, CalendarDays, CircleCheck, ClipboardCheck, Code, Download, ExternalLink, FileText, Gauge, Globe2,
  GraduationCap, Info, Lightbulb, Link2, Mail, MapPin, MessageSquare, Mic, PenLine, Plus, RefreshCw, Send, ShieldAlert,
  Sparkles, Telescope, Trash2, TriangleAlert, UserPlus, Users,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api, download } from "../api";
import { Checklist, Decision, DsaPill, HindiLinks, LevelPill, QuestionRow, RequirementGroup, ScoreBars, SourceLine, Tabs } from "../components/intel";
import {
  Button, Card, CompanyAvatar, CopyButton, Empty, ErrorText, Field, MatchLabel, Notice, Pill, ScoreRing, SkeletonPage,
  StatusBadge, Tag, Visa, buttonClass, formatDate, inputClass,
} from "../components/ui";
import type { JobDetails } from "../types";
import { useFetch } from "../useFetch";
import { SaveButton } from "./Jobs";

/** Source + freshness line: where it was listed, when we last saw / checked it, and the deadline (editable). */
function Freshness({ job, onChange }: { job: JobDetails; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  async function setDeadline(value: string) {
    await api(`/api/jobs/${job.id}`, { method: "PATCH", body: { deadline: value || null } });
    setEditing(false);
    onChange();
  }
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
      <span>Source: {job.source}{job.last_seen_at && ` · listed ${formatDate(job.last_seen_at)}`}</span>
      {job.agency && <Link to="/recruiter-jobs" className="font-medium text-amber-700 hover:underline">Advertised by recruiter {job.agency}</Link>}
      <span>{job.checked_at ? `Page checked ${formatDate(job.checked_at)}` : "Page not re-checked yet"}</span>
      {editing ? (
        <label className="inline-flex items-center gap-1.5">Deadline
          <input type="date" autoFocus defaultValue={job.deadline ?? ""} className={`${inputClass} h-7 w-36 py-0 text-xs`}
            onBlur={(e) => setDeadline(e.target.value)} onKeyDown={(e) => e.key === "Enter" && setDeadline((e.target as HTMLInputElement).value)} />
        </label>
      ) : (
        <button className="inline-flex items-center gap-1 hover:text-primary" onClick={() => setEditing(true)} title="Set or change the application deadline">
          <CalendarDays className="size-3.5" aria-hidden />{job.deadline ? <b className="text-warn">Apply by {formatDate(job.deadline)}</b> : "Add deadline"}
        </button>
      )}
    </div>
  );
}

const TABS = [
  { id: "overview", label: "Overview" }, { id: "match", label: "Match & gaps" }, { id: "interview", label: "Interview" },
  { id: "cv", label: "CV & ATS" }, { id: "outreach", label: "Outreach" }, { id: "jd", label: "Description" },
];

export default function JobDetail() {
  const { id } = useParams();
  const { data: job, error, reload } = useFetch<JobDetails>(`/api/jobs/${id}`);
  const { data: a, reload: reloadAnalysis } = useFetch<any>(`/api/jobs/${id}/analysis`);
  const [tab, setTab] = useState("overview");
  const [letter, setLetter] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function act(name: string, fn: () => Promise<void>) {
    try {
      setActionError(null);
      setBusy(name);
      await fn();
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorText error={error} />;
  if (!job || !a) return <SkeletonPage />;
  const file = (kind: string) => `${kind}_${job.company.replace(/\W+/g, "_")}.docx`;
  const refresh = () => { reload(); reloadAnalysis(); };

  const markApplied = () =>
    act("applied", async () => {
      await api(`/api/jobs/${id}/applied`, { body: { cover_letter: letter } });
      refresh();
    });

  return (
    <div className="space-y-5">
      <Link to="/jobs" className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> All jobs
      </Link>

      {/* Hero */}
      <section className="rounded-card border border-line bg-surface p-5 shadow-card sm:p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="flex min-w-0 gap-4">
            <CompanyAvatar name={job.company} size="lg" />
            <div className="min-w-0">
              <h1 className="text-xl font-bold leading-tight tracking-tight text-ink sm:text-[26px]">{job.title}</h1>
              <p className="mt-1 font-medium text-slate-700">{job.company} <span className="font-normal text-muted">· {a.company_type}</span></p>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted">
                <span className="inline-flex items-center gap-1"><MapPin className="size-3.5" />{job.location ?? "Location not specified"}</span>
                <span className="inline-flex items-center gap-1"><CalendarDays className="size-3.5" />Posted {formatDate(job.posted_at ?? job.discovered_at)}</span>
                <span>{a.role_family}</span>
              </div>
              <Freshness job={job} onChange={reload} />
              <div className="mt-3 flex flex-wrap gap-1.5">
                {job.application_id ? <StatusBadge status={job.application_status ?? "APPLIED"} /> : <MatchLabel match={job.match} />}
                <Visa status={job.visa_status} />
                <Pill className="bg-primary-50 text-primary">{a.germany.label}</Pill>
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-start gap-2"><SaveButton job={job} onChange={reload} /><ScoreRing value={a.scores.overall} size={88} label /></div>
        </div>
        <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-5">
          {job.application_url && (
            <a href={job.application_url} target="_blank" rel="noreferrer" className={buttonClass("primary")}>
              <ExternalLink className="size-4" aria-hidden /> Open job to apply
            </a>
          )}
          {job.application_id ? (
            <Link to="/applications" className={buttonClass("normal")}><Send className="size-4" aria-hidden /> View application</Link>
          ) : (
            <Button kind="success" icon={CircleCheck} loading={busy === "applied"} disabled={!!busy} onClick={markApplied}>Mark as applied</Button>
          )}
          <Link to={`/jobs/${id}/interview`} className={buttonClass("ai")}><Mic className="size-4" aria-hidden /> Prepare for interview</Link>
        </div>
        <div className="mt-3"><ErrorText error={actionError} /></div>
      </section>

      {job.status === "RISK" && <Notice tone="warn" icon={ShieldAlert}><b>Possible scam:</b> {job.risk_flags.join(", ")}</Notice>}
      {job.closed_at && (
        <Notice tone="warn" icon={TriangleAlert}>
          <b>This job looks closed</b> (checked {formatDate(job.closed_at)}: the page is gone or says the position is filled). It is hidden
          from your lists and the apply bot skips it.{" "}
          <button className="font-medium text-primary underline" onClick={async () => { await api(`/api/jobs/${id}`, { method: "PATCH", body: { reopen: true } }); reload(); }}>
            It is still open
          </button>
        </Notice>
      )}

      <Decision rec={a.recommendation} />

      <Tabs tabs={TABS.map((t) => t.id === "outreach" ? { ...t, badge: <span className="rounded-full bg-canvas px-1.5 text-xs">{a.health.score}</span> } : t)}
        active={tab} onChange={setTab} />

      {tab === "overview" && <Overview a={a} />}
      {tab === "match" && <MatchTab a={a} />}
      {tab === "interview" && <InterviewTab a={a} jobId={id!} onResearched={reloadAnalysis} />}
      {tab === "cv" && (
        <CvTab a={a} jobId={id!} busy={busy} act={act} letter={letter} setLetter={setLetter} warnings={warnings} setWarnings={setWarnings}
          file={file} />
      )}
      {tab === "outreach" && <OutreachTab a={a} jobId={id!} onChange={reloadAnalysis} />}
      {tab === "jd" && <DescriptionTab job={job} jobId={id!} />}
    </div>
  );
}

// ------------------------------------------------------------------ Overview

function Overview({ a }: { a: any }) {
  const r = a.readiness;
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <Card title="JD match score" subtitle={a.scores.uncertain ? "Wide range: the JD has few details" : "Rule-based, from your CV"} icon={Gauge}>
        <p className="mb-4 text-sm"><span className="text-3xl font-bold tabular-nums">{a.scores.overall}</span><span className="text-muted">/100</span>
          <span className="ml-2 text-muted">estimated {a.scores.range[0]}–{a.scores.range[1]}</span></p>
        <ScoreBars parts={a.scores.parts} />
      </Card>
      <Card title="Germany job fit" subtitle={a.germany_fit.tier} icon={Globe2}>
        <p className="mb-4 text-3xl font-bold tabular-nums">{a.germany_fit.overall}<span className="text-base font-normal text-muted">/100</span></p>
        {a.germany_fit.blocker && <div className="mb-3"><Notice tone="warn" icon={TriangleAlert}>{a.germany_fit.blocker}</Notice></div>}
        <ScoreBars parts={a.germany_fit.parts} />
      </Card>
      <Card title="Applying from India" subtitle={a.germany.label} icon={Globe2}>
        <p className="mb-3 text-xs text-muted">{a.germany.why}</p>
        <dl className="divide-y divide-line text-sm">
          {a.germany.checks.map((c: any) => (
            <div key={c.q} className="flex justify-between gap-3 py-1.5"><dt className="text-muted">{c.q}</dt><dd className="text-right font-medium">{c.a}</dd></div>
          ))}
        </dl>
      </Card>
      <Card title="Estimated hiring readiness" subtitle={r.note} icon={ClipboardCheck} className="lg:col-span-3">
        <div className="grid gap-5 md:grid-cols-3">
          <div className="space-y-3">
            <p className="text-sm text-muted">Current fit <b className="ml-1 text-2xl text-ink">{r.current}</b> → after preparation <b className="ml-1 text-2xl text-ok">{r.after_preparation}</b></p>
            {r.learnable_gaps.length > 0 && <p className="text-xs text-muted">By learning: {r.learnable_gaps.join(", ")}</p>}
            <div className="flex flex-wrap gap-2">
              <LevelPill prefix="CV shortlist" level={r.shortlist} />
              <LevelPill prefix="Technical interview" level={r.technical} />
              <LevelPill prefix="Final hiring" level={r.final} />
            </div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Why you can get shortlisted</h3>
            <ul className="space-y-1.5 text-sm">{r.why_shortlist.map((x: string) => <li key={x} className="flex gap-2"><CircleCheck className="mt-0.5 size-4 shrink-0 text-ok-strong" />{x}</li>)}</ul>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Biggest risks (ranked)</h3>
            {r.risks.length ? (
              <ol className="space-y-1.5 text-sm">{r.risks.map((x: any) => (
                <li key={x.risk} className="flex gap-2"><TriangleAlert className={`mt-0.5 size-4 shrink-0 ${x.severity >= 4 ? "text-bad-strong" : "text-amber-500"}`} />{x.risk}</li>
              ))}</ol>
            ) : <p className="text-sm text-muted">No major risks found.</p>}
          </div>
        </div>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ Match & gaps

function MatchTab({ a }: { a: any }) {
  const q = a.requirements;
  return (
    <div className="space-y-5">
      <Card title="Job information" subtitle="Only what the JD says. Missing = “Not specified”" icon={Info}>
        <dl className="grid gap-x-8 sm:grid-cols-2">
          {Object.entries(a.job_information).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 border-b border-line py-2 text-sm">
              <dt className="shrink-0 text-muted">{k}</dt>
              <dd className={`min-w-0 break-words text-right ${v === "Not specified" ? "text-slate-400" : "font-medium text-ink"}`}>{v as string}</dd>
            </div>
          ))}
        </dl>
      </Card>
      <Card title="JD requirements vs your CV" subtitle="Strong = proven by a CV project · Partial = listed or related · Missing = not on your CV" icon={ClipboardCheck}>
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          <RequirementGroup title="Must have" items={q.must} />
          <RequirementGroup title="Strongly preferred" items={q.preferred} />
          <RequirementGroup title="Nice to have" items={q.nice} />
          <RequirementGroup title="Soft skills" items={q.soft} />
          <RequirementGroup title="Domain knowledge" items={q.domain} />
          <RequirementGroup title="Experience" items={q.experience} empty="Not specified" />
          <RequirementGroup title="Education" items={q.education} empty="Not specified" />
          <RequirementGroup title="Language" items={q.language} />
        </div>
      </Card>
      <Card ai title="What to learn first" subtitle="Ranked by learning ROI: importance here × demand across your target jobs × speed to learn" icon={GraduationCap}>
        {!a.skill_gaps.length ? <p className="text-sm text-muted">No skill gaps for this JD.</p> : (
          <>
            <ol className="space-y-2 lg:hidden">
              {a.skill_gaps.map((g: any) => (
                <li key={g.skill} className="rounded-control border border-line p-3 text-sm">
                  <div className="flex items-center justify-between gap-2"><b>#{g.priority} {g.skill}</b><span className="rounded-full bg-ai-50 px-2 py-0.5 text-xs font-bold text-ai">ROI {g.roi}</span></div>
                  <p className="mt-1 text-xs text-muted">{g.importance} importance · {g.time} · interview {g.interview} · in {g.jobs_share}% of your target jobs</p>
                  <p className="mt-1 text-xs">Now: {g.current} → {g.target}</p>
                  {g.cannot_fake && <p className="mt-1 text-xs text-bad">Needs real production experience: can't be learned quickly</p>}
                  {!g.cannot_fake && <HindiLinks links={g.learn_hindi} />}
                </li>
              ))}
            </ol>
            <div className="hidden overflow-x-auto lg:block">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>{["#", "Skill", "Importance", "Current → target", "Time", "Interview", "CV", "Target jobs", "ROI"].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {a.skill_gaps.map((g: any) => (
                    <tr key={g.skill}>
                      <td className="px-3 py-2 text-muted">{g.priority}</td>
                      <td className="px-3 py-2 font-semibold">{g.skill}{g.cannot_fake && <span className="block text-xs font-normal text-bad">needs real experience</span>}
                        {!g.cannot_fake && <div className="max-w-[260px] font-normal"><HindiLinks links={g.learn_hindi} /></div>}</td>
                      <td className="px-3 py-2">{g.importance}</td>
                      <td className="max-w-[260px] px-3 py-2 text-xs text-muted">{g.current} → {g.target}</td>
                      <td className="whitespace-nowrap px-3 py-2">{g.time}</td>
                      <td className="px-3 py-2">{g.interview}</td>
                      <td className="px-3 py-2">{g.cv_importance}</td>
                      <td className="px-3 py-2 tabular-nums">{g.jobs_share}%</td>
                      <td className="px-3 py-2"><span className="rounded-full bg-ai-50 px-2 py-0.5 text-xs font-bold text-ai">{g.roi}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-muted">Times are rough estimates for working knowledge. Don't learn everything: the top 1–2 give the most.
              Hindi links open a YouTube search on channels checked on 7 Oct 2026 (CodeWithHarry, CampusX, Chai aur Code, Apna College, TrainWithShubham, CloudFolks HUB Hindi…).</p>
          </>
        )}
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ Interview

function InterviewTab({ a, jobId, onResearched }: { a: any; jobId: string; onResearched: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const research = a.research;

  async function runResearch(refresh = false) {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/jobs/${jobId}/research${refresh ? "?refresh=true" : ""}`, { method: "POST" });
      onResearched();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <Card ai title="Company & interview-process research" icon={Telescope}
        subtitle={research ? `Researched ${formatDate(research.researched_at)} with web search · every claim has a source` : "Official pages, Glassdoor, Kununu, Reddit, Blind… with sources and confidence"}
        right={a.ai_available && (
          <Button kind={research ? "normal" : "ai"} icon={research ? RefreshCw : Telescope} loading={busy} onClick={() => runResearch(!!research)}>
            {research ? "Refresh" : "Research company"}
          </Button>
        )}>
        <ErrorText error={error} />
        {!a.ai_available && (
          <Notice tone="ai" icon={Sparkles}>
            Research needs AI: add <code className="rounded bg-white px-1">AI_API_KEY</code> to the <code className="rounded bg-white px-1">.env</code> file and restart the backend.
            Until then, everything below is estimated from the JD and the company type (and labelled so).
          </Notice>
        )}
        {busy && <p className="mt-3 text-sm text-muted">Searching the web and checking sources… this can take a minute.</p>}
        {research && (
          <div className="mt-2 space-y-5">
            {research.summary && <p className="text-sm text-slate-700">{research.summary}</p>}
            {research.interview_rounds?.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold">Likely interview process</h3>
                <ol className="relative space-y-3 border-l-2 border-ai-100 pl-5">
                  {research.interview_rounds.map((r: any) => (
                    <li key={r.order} className="text-sm">
                      <span className="absolute -left-[9px] mt-1 size-4 rounded-full border-2 border-white bg-ai" />
                      <b>Round {r.order}: {r.name}</b> <span className="text-muted">· {r.duration}</span>
                      <p className="text-slate-600">{r.evaluates}</p>
                      <SourceLine status={r.status} url={r.source_url} confidence={r.confidence} />
                    </li>
                  ))}
                </ol>
                {research.process_conclusion && <p className="mt-3 text-sm"><b>Conclusion:</b> {research.process_conclusion}</p>}
                {research.conflicts?.length > 0 && (
                  <Notice tone="warn" icon={TriangleAlert}><b>Sources disagree:</b><ul className="list-disc pl-5">{research.conflicts.map((c: string) => <li key={c}>{c}</li>)}</ul></Notice>
                )}
              </div>
            )}
            <div>
              <h3 className="mb-2 text-sm font-semibold">Company facts</h3>
              <ul className="divide-y divide-line rounded-control border border-line">
                {research.facts.map((f: any, i: number) => (
                  <li key={i} className="grid gap-1 px-3 py-2 text-sm sm:grid-cols-[180px_1fr]">
                    <span className="font-medium capitalize text-muted">{f.topic.replaceAll("_", " ")}</span>
                    <span className="min-w-0"><span className={f.status === "not_found" ? "text-slate-400" : ""}>{f.value}</span>
                      <SourceLine status={f.status} url={f.source_url} type={f.source_type} date={f.published} confidence={f.confidence} /></span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="DSA requirement" subtitle={a.dsa.basis} icon={Code}>
          <div className="flex flex-wrap items-center gap-2"><DsaPill level={a.dsa.level} prefix="DSA" /><Tag>{a.dsa.company_type}</Tag></div>
          <p className="mt-3 text-sm text-slate-700">{a.dsa.why}</p>
          {a.dsa.reported_level && <p className="mt-2 text-sm"><b>Reported:</b> {a.dsa.reported_level}: {a.dsa.reported_evidence} <SourceLine status="reported" url={a.dsa.reported_source} /></p>}
          <h3 className="mb-2 mt-4 text-sm font-semibold">Prepare (~{a.dsa.problems} problems)</h3>
          <div className="flex flex-wrap gap-1.5">{a.dsa.required.map((t: string) => <Pill key={t} className="bg-primary-50 text-primary">{t}</Pill>)}</div>
          <h3 className="mb-2 mt-3 text-sm font-semibold text-muted">Optional</h3>
          <div className="flex flex-wrap gap-1.5">{a.dsa.optional.map((t: string) => <Pill key={t} className="bg-neutral-bg text-neutral">{t}</Pill>)}</div>
          <div className="mt-3"><HindiLinks links={a.dsa.learn_hindi} compact /></div>
        </Card>
        <Card title="Questions to ask them" subtitle="Specific to this company and role" icon={MessageSquare}>
          <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-700">{a.questions_to_ask.map((q: string) => <li key={q}>{q}</li>)}</ol>
        </Card>
      </div>

      <Card title="Top predicted questions" subtitle="From the JD, your CV and (if researched) candidate reports" icon={Brain}
        right={<Link to={`/jobs/${jobId}/interview`} className={buttonClass("ai")}><Mic className="size-4" /> Practice (mock interview)</Link>}>
        <p className="mb-2 text-xs text-muted">Open “How to answer” for the structure, the CV facts to use, pitfalls and an opening line.</p>
        <ol className="divide-y divide-line">
          {a.predicted_questions.map((q: any, i: number) => <QuestionRow key={q.question} q={q} index={i + 1} jobId={jobId} ai={a.ai_available} />)}
        </ol>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------ CV & ATS

function CvTab({ a, jobId, busy, act, letter, setLetter, warnings, setWarnings, file }: any) {
  const plan = a.cv_plan;
  const ats = a.ats;
  return (
    <div className="space-y-5">
      <Card ai title="Your application documents" subtitle="One standard CV for every application; the cover letter is written for this job from your CV" icon={Sparkles}>
        <div>
          <div className="flex flex-wrap gap-2">
            <Button kind="ai" icon={Download} loading={busy === "cv"} disabled={!!busy}
              onClick={() => act("cv", () => download(`/api/jobs/${jobId}/cv.docx`, "CV.docx"))}>Standard CV (.docx)</Button>
            <Button icon={PenLine} loading={busy === "letter"} disabled={!!busy} onClick={() => act("letter", async () => {
              const r = await api(`/api/jobs/${jobId}/cover-letter`, { method: "POST" });
              setLetter(r.text);
              setWarnings(r.warnings);
            })}>Write cover letter</Button>
          </div>
        </div>
        {letter !== null && (
          <div className="mt-4 space-y-3">
            {warnings.map((w: string) => <Notice key={w} tone="warn" icon={TriangleAlert}>{w}</Notice>)}
            <label className="block"><span className="sr-only">Cover letter</span>
              <textarea className={inputClass} rows={14} value={letter} onChange={(e) => setLetter(e.target.value)} /></label>
            <div className="flex flex-wrap gap-2">
              <CopyButton text={letter} />
              <Button icon={Download} loading={busy === "letterdoc"} disabled={!!busy}
                onClick={() => act("letterdoc", () => download(`/api/jobs/${jobId}/cover-letter.docx`, file("Cover_Letter"), { text: letter }))}>Cover letter (.docx)</Button>
            </div>
          </div>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="ATS keywords" subtitle={`Match now ${ats.match_now}% → ${ats.match_possible}% with legitimate additions`} icon={FileText}>
          <h3 className="mb-2 text-sm font-semibold">Already on your CV</h3>
          <div className="flex flex-wrap gap-1.5">{ats.present.length ? ats.present.map((k: string) => <Pill key={k} className="bg-ok-bg text-ok">{k}</Pill>) : <span className="text-sm text-muted">None</span>}</div>
          <h3 className="mb-2 mt-4 text-sm font-semibold">Can legitimately add</h3>
          {ats.can_add.length ? <ul className="space-y-1 text-sm">{ats.can_add.map((k: any) => <li key={k.keyword}><b>{k.keyword}</b>: <span className="text-muted">{k.how}</span></li>)}</ul>
            : <p className="text-sm text-muted">Nothing: your CV already names all the JD skills you have.</p>}
          <h3 className="mb-2 mt-4 text-sm font-semibold text-bad">Must NOT add</h3>
          {ats.must_not_add.length ? <ul className="space-y-1 text-sm">{ats.must_not_add.map((k: any) => <li key={k.keyword}><b>{k.keyword}</b>: <span className="text-muted">{k.how}</span></li>)}</ul>
            : <p className="text-sm text-muted">None.</p>}
        </Card>
        <Card title="What this job looks for" subtitle="Ideas for your next standard-CV update (applies to every job): never invent experience" icon={ClipboardCheck}>
          <dl className="space-y-3 text-sm">
            <div><dt className="font-semibold">Skills to list first</dt><dd className="text-muted">{plan.skills_first.join(", ") || "–"}</dd></div>
            <div><dt className="font-semibold">Projects to emphasize</dt><dd className="text-muted">{plan.emphasize_projects.join(" · ") || "–"}</dd></div>
            <div><dt className="font-semibold">Projects to shorten</dt><dd className="text-muted">{plan.shorten_projects.join(" · ") || "–"}</dd></div>
            {plan.weak_bullets.length > 0 && (
              <div><dt className="font-semibold">Bullets that would be stronger with a real number</dt>
                <dd><ul className="mt-1 space-y-2">{plan.weak_bullets.map((b: any) => (
                  <li key={b.bullet} className="rounded-control bg-canvas p-2 text-xs"><span className="text-muted">{b.where}:</span> {b.bullet}<span className="mt-1 block text-primary">{b.tip}</span></li>
                ))}</ul></dd></div>
            )}
          </dl>
        </Card>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ Outreach

const KINDS = [["recruiter", "Recruiter for this job/team (Tier 1)"], ["talent_acquisition", "Talent Acquisition (Tier 2)"],
  ["hiring_manager", "Hiring / Engineering Manager (Tier 3)"], ["department_head", "Department head (Tier 4)"], ["referral", "Employee for a referral"]];

function OutreachTab({ a, jobId, onChange }: { a: any; jobId: string; onChange: () => void }) {
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<{ id: number; msg: any } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function patch(contactId: number, body: object) {
    try { await api(`/api/contacts/${contactId}`, { method: "PATCH", body }); onChange(); } catch (e) { setError((e as Error).message); }
  }

  return (
    <div className="space-y-5">
      <Notice icon={Users}>
        <b>Quality over quantity.</b> 1 relevant recruiter, 1 hiring manager, 1 follow-up. Every message is personal; the app never sends anything:
        you copy it and send it yourself.
      </Notice>
      <ErrorText error={error} />
      <div className="grid gap-5 lg:grid-cols-3">
        <Card title={`Application health: ${a.health.score}/100`} subtitle="Is your CV likely to reach a human?" icon={ClipboardCheck}>
          <Checklist items={a.health.items} />
        </Card>
        <Card title="Outreach plan" subtitle="Do these in order" icon={Send}>
          <Checklist items={a.outreach_plan.map((s: any) => ({ label: `${s.step}. ${s.text}`, done: s.done }))} />
        </Card>
        <Card title="Find the right person" subtitle="Open these searches yourself (no scraping)" icon={Link2}>
          <ul className="space-y-2">
            {Object.entries(a.search_links).map(([label, url]) => (
              <li key={label}><a href={url as string} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
                {label} <ExternalLink className="size-3.5" /></a></li>
            ))}
          </ul>
          {a.follow_ups.length > 0 && (
            <div className="mt-4 border-t border-line pt-3">
              <h3 className="mb-2 text-sm font-semibold">Follow-ups</h3>
              <ul className="space-y-1 text-sm">{a.follow_ups.map((f: any) => <li key={f.text} className={f.overdue ? "font-medium text-warn" : "text-muted"}>{f.text}</li>)}</ul>
            </div>
          )}
        </Card>
      </div>

      <Card title="People for this job" subtitle={`${a.contacts.length}/3 · ranked by tier`} icon={UserPlus}
        right={a.contacts.length < 3 && <Button icon={adding ? undefined : Plus} onClick={() => setAdding(!adding)}>{adding ? "Cancel" : "Add person"}</Button>}>
        {adding && <ContactForm jobId={jobId} onSaved={() => { setAdding(false); onChange(); }} />}
        {!a.contacts.length && !adding ? (
          <Empty icon={UserPlus} title="No one identified yet" text="Use the search links above, then add the recruiter (or hiring manager) you found: name, role and LinkedIn link."
            action={<Button kind="primary" icon={Plus} onClick={() => setAdding(true)}>Add person</Button>} />
        ) : (
          <ul className="divide-y divide-line">
            {[...a.contacts].sort((x: any, y: any) => x.tier - y.tier).map((c: any) => (
              <li key={c.id} className="py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">{c.name} <span className="font-normal text-muted">· {c.role}</span></p>
                    <p className="text-xs text-muted">Tier {c.tier} · {c.kind_label}{c.relevance ? ` · ${c.relevance}` : ""} · {c.confidence} confidence</p>
                    <div className="mt-1 flex flex-wrap gap-3 text-xs">
                      {c.linkedin_url && <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">LinkedIn ↗</a>}
                      {c.email && <span className="inline-flex items-center gap-1"><Mail className="size-3" />{c.email}</span>}
                      {c.source_url && <a href={c.source_url} target="_blank" rel="noreferrer" className="text-muted hover:underline">where found ↗</a>}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {c.contacted_at ? <Pill className="bg-pending-bg text-pending">Contacted {formatDate(c.contacted_at)}</Pill>
                      : <Button onClick={() => patch(c.id, { contacted: true })}>Mark contacted</Button>}
                    {c.contacted_at && (c.replied_at ? <Pill className="bg-ok-bg text-ok">Replied</Pill> : <Button onClick={() => patch(c.id, { replied: true })}>Mark replied</Button>)}
                    {c.contacted_at && !c.replied_at && !c.followed_up_at && <Button kind="ghost" onClick={() => patch(c.id, { followed_up: true })}>Followed up</Button>}
                    <Button kind="ai" icon={PenLine} onClick={async () => setOpen(open?.id === c.id ? null : { id: c.id, msg: await api(`/api/contacts/${c.id}/message`) })}>Message</Button>
                    <Button kind="ghost" icon={Trash2} title={`Remove ${c.name}`} onClick={async () => { await api(`/api/contacts/${c.id}`, { method: "DELETE" }); onChange(); }} />
                  </div>
                </div>
                {open && open.id === c.id && <Messages msg={open.msg} />}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Messages({ msg }: { msg: any }) {
  const parts: [string, string][] = [[`LinkedIn connection note (${msg.note_length}/300)`, msg.note], ["LinkedIn message (after they accept)", msg.message],
    ["Follow-up (once, after ~7 days)", msg.follow_up]];
  if (msg.email_allowed) parts.push([`Email: ${msg.email_subject}`, `${msg.email_subject}\n\n${msg.email_body}`]);
  return (
    <div className="mt-3 space-y-3 rounded-control bg-ai-50 p-3">
      {parts.map(([title, text]) => (
        <div key={title} className="rounded-control border border-ai-100 bg-surface p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2"><b className="text-sm">{title}</b><CopyButton text={text} /></div>
          <p className="whitespace-pre-wrap break-words text-sm text-slate-700">{text}</p>
        </div>
      ))}
      {!msg.email_allowed && <p className="text-xs text-muted">No email shown: add a publicly listed address to the person to get an email draft.</p>}
    </div>
  );
}

function ContactForm({ jobId, onSaved }: { jobId: string; onSaved: () => void }) {
  const [f, setF] = useState({ name: "", role: "", kind: "recruiter", linkedin_url: "", email: "", source_url: "", relevance: "", confidence: "Medium" });
  const [error, setError] = useState<string | null>(null);
  const bind = (k: keyof typeof f) => ({ value: f[k], onChange: (e: any) => setF({ ...f, [k]: e.target.value }) });
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api(`/api/jobs/${jobId}/contacts`, { body: Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v || null])) });
      onSaved();
    } catch (err) { setError((err as Error).message); }
  }
  return (
    <form onSubmit={submit} className="mb-4 grid gap-4 rounded-control border border-line bg-canvas p-4 sm:grid-cols-2">
      <Field label="Name"><input required className={inputClass} {...bind("name")} /></Field>
      <Field label="Role (as on their profile)"><input required className={inputClass} placeholder="Technical Recruiter" {...bind("role")} /></Field>
      <Field label="Relationship to this job"><select className={inputClass} {...bind("kind")}>{KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
      <Field label="LinkedIn profile link"><input type="url" className={inputClass} placeholder="https://www.linkedin.com/in/…" {...bind("linkedin_url")} /></Field>
      <Field label="Public email (only if publicly listed)"><input type="email" className={inputClass} {...bind("email")} /></Field>
      <Field label="Where you found them (link)"><input type="url" className={inputClass} {...bind("source_url")} /></Field>
      <Field label="Why relevant"><input className={inputClass} placeholder="Recruits backend engineers in Berlin" {...bind("relevance")} /></Field>
      <Field label="Confidence"><select className={inputClass} {...bind("confidence")}>{["High", "Medium", "Low"].map((c) => <option key={c}>{c}</option>)}</select></Field>
      <div className="space-y-2 sm:col-span-2"><ErrorText error={error} /><Button type="submit" kind="primary" icon={UserPlus}>Save person</Button></div>
    </form>
  );
}

// ------------------------------------------------------------------ Description

function DescriptionTab({ job, jobId }: { job: JobDetails; jobId: string }) {
  const [versions, setVersions] = useState<any[] | null>(null);
  return (
    <Card title="Job description" icon={FileText}
      right={job.versions > 1 && (
        <Button onClick={async () => setVersions(versions ? null : await api(`/api/jobs/${jobId}/versions`))}>{versions ? "Hide" : "Show"} all {job.versions} versions</Button>
      )}>
      {versions ? versions.map((v) => (
        <details key={v.id} className="mb-2 rounded-control border border-line p-3 text-sm">
          <summary className="cursor-pointer font-medium">Version {v.version} · {new Date(v.captured_at).toLocaleString()} · {v.source}</summary>
          <pre className="mt-2 whitespace-pre-wrap break-words font-sans text-slate-700">{v.text}</pre>
        </details>
      )) : <pre className="max-h-[36rem] overflow-auto whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-700">{job.description}</pre>}
      <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted"><Lightbulb className="size-3.5" />Found on {[...new Set(job.sources.map((s) => s.source))].join(", ")} · {formatDate(job.discovered_at)}</p>
    </Card>
  );
}
