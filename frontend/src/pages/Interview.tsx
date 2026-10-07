// "Prepare for interview": the complete package for one job, and a mock interview (one question at a time).
import { ArrowLeft, Brain, ChevronDown, CircleCheck, Code, Lightbulb, MessageSquare, Mic, Play, Send, Sparkles, Target, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { AnswerGuide, QuestionRow, ScoreBars, SourceLine } from "../components/intel";
import { Button, Card, Chip, ErrorText, Notice, PageTitle, Pill, ProgressBar, SkeletonPage, Tag, inputClass } from "../components/ui";
import { useFetch } from "../useFetch";

export default function Interview() {
  const { id } = useParams();
  const { data: p, error } = useFetch<any>(`/api/jobs/${id}/interview-package`);
  const [mock, setMock] = useState(false);

  if (error) return <ErrorText error={error} />;
  if (!p) return <SkeletonPage />;
  return (
    <div className="space-y-5">
      <Link to={`/jobs/${id}`} className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink"><ArrowLeft className="size-4" /> Back to the job</Link>
      <PageTitle title={`Interview prep · ${p.company.name}`} subtitle={`${p.role.title} · ${p.company.type}`}
        right={<Button kind="ai" icon={mock ? undefined : Mic} onClick={() => setMock(!mock)}>{mock ? "Back to prep" : "Start mock interview"}</Button>} />

      {mock ? <MockInterview jobId={id!} pkg={p} /> : <Package p={p} jobId={id!} />}
    </div>
  );
}

function Section({ title, children, open = false, count }: { title: string; children: React.ReactNode; open?: boolean; count?: number }) {
  return (
    <details open={open} className="group rounded-control border border-line bg-surface">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-semibold [&::-webkit-details-marker]:hidden">
        {title}{count !== undefined && <span className="rounded-full bg-canvas px-1.5 text-xs font-normal text-muted">{count}</span>}
        <ChevronDown className="ml-auto size-4 text-muted transition-transform group-open:rotate-180" aria-hidden />
      </summary>
      <div className="border-t border-line px-4 py-3 text-sm">{children}</div>
    </details>
  );
}

function Package({ p, jobId }: { p: any; jobId: string }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Interview readiness" subtitle={p.readiness.note} icon={Target}>
          <ScoreBars parts={p.readiness.areas} />
          <p className="mt-4 text-sm"><b>Biggest weaknesses:</b> {p.readiness.weakest.join(", ")}</p>
          <p className="text-sm text-muted">Recommended preparation: ~{p.readiness.days} days</p>
        </Card>
        <Card title="Your strengths" icon={CircleCheck}>
          <ul className="space-y-1.5 text-sm">{p.strengths.map((s: string) => <li key={s} className="flex gap-2"><CircleCheck className="mt-0.5 size-4 shrink-0 text-ok-strong" />{s}</li>)}</ul>
        </Card>
        <Card title="Weaknesses to prepare for" icon={TriangleAlert}>
          {p.weaknesses.length ? <ul className="space-y-1.5 text-sm">{p.weaknesses.map((s: string) => <li key={s} className="flex gap-2"><TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-500" />{s}</li>)}</ul>
            : <p className="text-sm text-muted">None found.</p>}
        </Card>
      </div>

      <Card ai title="Likely interview stages" icon={Sparkles}
        subtitle={p.stages.length ? "From company research (see sources)" : "Not researched yet: open the job's Interview tab and click “Research company”"}>
        {p.stages.length ? (
          <ol className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {p.stages.map((s: any) => (
              <li key={s.order} className="rounded-control border border-ai-100 bg-ai-50/50 p-3 text-sm">
                <b>Round {s.order}: {s.name}</b> <span className="text-muted">· {s.duration}</span>
                <p className="mt-1 text-slate-600">{s.evaluates}</p>
                <SourceLine status={s.status} url={s.source_url} confidence={s.confidence} />
              </li>
            ))}
          </ol>
        ) : <p className="text-sm text-muted">Typical in Germany (estimate, not company-specific): recruiter call → technical interview / coding → (take-home or system design) → hiring manager / team fit.</p>}
        {p.process_conclusion && <p className="mt-3 text-sm"><b>Conclusion:</b> {p.process_conclusion}</p>}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-3">
          <h2 className="flex items-center gap-2 text-base font-semibold"><Brain className="size-4 text-ai" /> Questions by category</h2>
          {Object.entries(p.questions).map(([cat, qs]: [string, any]) => (
            <Section key={cat} title={cat} count={qs.length} open={cat === "Project deep dive"}>
              <ul className="divide-y divide-line">{qs.map((q: any) => <QuestionRow key={q.question} q={q} jobId={jobId} ai={p.ai_available} />)}</ul>
              {p.answer_structures[cat] && (
                <p className="mt-3 rounded-control bg-canvas p-2 text-xs"><b>Good answer structure:</b> {p.answer_structures[cat].join(" → ")}</p>
              )}
            </Section>
          ))}
        </div>
        <div className="space-y-3">
          <h2 className="flex items-center gap-2 text-base font-semibold"><Code className="size-4 text-primary" /> Technical preparation</h2>
          <Section title={`DSA: ${p.dsa.level}`} open>
            <p className="text-muted">{p.dsa.why}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">{p.dsa.required.map((t: string) => <Pill key={t} className="bg-primary-50 text-primary">{t}</Pill>)}</div>
          </Section>
          <Section title="Technical topics to revise" count={p.topics.length}>
            <div className="space-y-3">{p.topics.map((t: any) => (
              <div key={t.skill}><div className="mb-1 flex items-center gap-2"><b>{t.skill}</b>{t.you_have_it ? <Tag color="bg-ok-bg text-ok">on your CV</Tag> : <Tag color="bg-warn-bg text-warn">new for you</Tag>}</div>
                <ul className="list-disc space-y-0.5 pl-5 text-slate-600">{t.topics.map((x: string) => <li key={x}>{x}</li>)}</ul></div>
            ))}</div>
          </Section>
          <Section title="Your stories (from your CV)" count={p.stories.length}>
            <ul className="space-y-2">{p.stories.map((s: any) => <li key={s.story}><b>{s.skill}</b> · {s.where}: <span className="text-slate-600">{s.story}</span></li>)}</ul>
          </Section>
          {p.gaps.length > 0 && (
            <Section title="Gaps to study" count={p.gaps.length}>
              <ul className="space-y-2">{p.gaps.map((g: any) => <li key={g.skill}><b>{g.skill}</b>: <span className="text-slate-600">{g.advice}</span></li>)}</ul>
            </Section>
          )}
          <Section title="Questions to ask the interviewer" count={p.questions_to_ask.length}>
            <ol className="list-decimal space-y-1 pl-5 text-slate-600">{p.questions_to_ask.map((q: string) => <li key={q}>{q}</li>)}</ol>
          </Section>
          {p.company.facts.length > 0 && (
            <Section title="Company overview (researched)" count={p.company.facts.length}>
              {p.company.summary && <p className="mb-2">{p.company.summary}</p>}
              <ul className="space-y-2">{p.company.facts.filter((f: any) => f.status !== "not_found").map((f: any, i: number) => (
                <li key={i}><b className="capitalize">{f.topic.replaceAll("_", " ")}:</b> {f.value}<SourceLine status={f.status} url={f.source_url} date={f.published} /></li>
              ))}</ul>
            </Section>
          )}
        </div>
      </div>
      <p className="text-xs text-muted">Job: <Link to={`/jobs/${jobId}`} className="text-primary hover:underline">{p.role.title}</Link>. Questions marked “Estimated” come from the JD and your CV; “Reported” ones have a source.</p>
    </div>
  );
}

// ------------------------------------------------------------------ mock interview

const SCORE_NAMES: Record<string, string> = { technical_accuracy: "Technical accuracy", communication: "Communication", structure: "Structure",
  confidence: "Confidence", completeness: "Completeness", clarity: "Clarity" };

function MockInterview({ jobId, pkg }: { jobId: string; pkg: any }) {
  const [session, setSession] = useState<any>(null);
  const [cats, setCats] = useState<string[]>([]);
  const [answer, setAnswer] = useState("");
  const [selfScore, setSelfScore] = useState(60);
  const [showStructure, setShowStructure] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const last = session?.answers?.[session.answers.length - 1];

  async function run(fn: () => Promise<void>) {
    setBusy(true); setError(null);
    try { await fn(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  if (!session) {
    return (
      <Card ai title="Mock interview" subtitle="10 likely questions for this job, one at a time. Answer as you would out loud." icon={Mic}>
        {!pkg.ai_available && (
          <Notice tone="ai" icon={Sparkles}>Claude is not configured, so you grade yourself against the ideal answer structure.
            Add <code className="rounded bg-white px-1">AI_API_KEY</code> to <code className="rounded bg-white px-1">.env</code> for real grading (accuracy, communication, structure…).</Notice>
        )}
        <p className="mb-2 mt-4 text-sm font-medium">Focus (optional)</p>
        <div className="flex flex-wrap gap-2">
          {Object.keys(pkg.questions).map((c) => <Chip key={c} on={cats.includes(c)} onClick={() => setCats(cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c])}>{c}</Chip>)}
        </div>
        <ErrorText error={error} />
        <div className="mt-4"><Button kind="ai" icon={Play} loading={busy} onClick={() => run(async () => setSession(await api(`/api/jobs/${jobId}/mock`, { body: { categories: cats.length ? cats : null } })))}>Start</Button></div>
      </Card>
    );
  }

  const submit = () => run(async () => {
    setSession(await api(`/api/mock/${session.id}/answer`, { body: { answer, self_score: session.ai_available ? null : selfScore } }));
    setAnswer(""); setShowStructure(false);
  });
  const structure = session.next ? (pkg.answer_structures[session.next.category] ?? pkg.answer_structures.Technical) : [];
  const guideFor = (question: string) => Object.values(pkg.questions).flat().find((q: any) => q.question === question);

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      <div className="min-w-0 space-y-5">
        {last && <Feedback a={last} />}
        {session.next ? (
          <Card ai title={`Question ${session.answered + 1} of ${session.total}`} subtitle={`${session.next.category} · probability ${session.next.probability}`} icon={MessageSquare}>
            <p className="text-lg font-semibold leading-snug text-ink">{session.next.question}</p>
            <label className="mt-4 block"><span className="sr-only">Your answer</span>
              <textarea className={inputClass} rows={8} placeholder="Type your answer as you would say it…" value={answer} onChange={(e) => setAnswer(e.target.value)} /></label>
            {!session.ai_available && (
              <div className="mt-3 space-y-3">
                {showStructure ? (
                  <>
                    {guideFor(session.next.question)
                      ? <AnswerGuide q={guideFor(session.next.question)} jobId={jobId} ai={false} />
                      : <p className="rounded-control bg-canvas p-3 text-sm"><b>Ideal structure:</b> {structure.join(" → ")}</p>}
                    <label className="block text-sm"><span className="font-medium">Rate your answer: {selfScore}/100</span>
                      <input type="range" min={0} max={100} step={5} value={selfScore} onChange={(e) => setSelfScore(Number(e.target.value))} className="mt-1 w-full accent-[var(--color-ai)]" /></label>
                  </>
                ) : <Button disabled={!answer.trim()} onClick={() => setShowStructure(true)}>Compare with the ideal structure</Button>}
              </div>
            )}
            <ErrorText error={error} />
            <div className="mt-4 flex flex-wrap gap-2">
              <Button kind="ai" icon={Send} loading={busy} disabled={!answer.trim() || (!session.ai_available && !showStructure)} onClick={submit}>
                {session.ai_available ? "Submit for grading" : "Save and next"}
              </Button>
            </div>
          </Card>
        ) : (
          <Card title="Mock interview finished" icon={CircleCheck}>
            <p className="text-sm">Average score: <b className="text-2xl">{session.average ?? "–"}</b>{session.average !== null && "/100"}</p>
            <div className="mt-4"><Button kind="ai" icon={Play} onClick={() => setSession(null)}>New mock interview</Button></div>
          </Card>
        )}
      </div>
      <Card title="Progress" icon={Target}>
        <ProgressBar tone="ai" value={(100 * session.answered) / session.total} label="Questions answered" />
        <p className="mt-2 text-sm text-muted">{session.answered}/{session.total} answered{session.average !== null && ` · average ${session.average}`}</p>
        <ol className="mt-3 space-y-1.5 text-sm">
          {session.answers.map((a: any, i: number) => (
            <li key={i} className="flex justify-between gap-2"><span className="truncate">{i + 1}. {a.question}</span><b className="shrink-0 tabular-nums">{a.grade?.overall ?? "–"}</b></li>
          ))}
        </ol>
      </Card>
    </div>
  );
}

function Feedback({ a }: { a: any }) {
  const g = a.grade;
  return (
    <Card title={`Feedback · ${g.overall ?? "–"}/100`} subtitle={g.by === "claude" ? "Graded by Claude" : "Self-rated"} icon={Lightbulb}>
      <p className="mb-3 text-sm text-muted">Q: {a.question}</p>
      {Object.keys(g.scores ?? {}).length > 0 && <div className="mb-4"><ScoreBars parts={Object.fromEntries(Object.entries(g.scores).map(([k, v]) => [SCORE_NAMES[k] ?? k, v as number]))} /></div>}
      <div className="grid gap-4 text-sm md:grid-cols-2">
        {[["What was good", g.good], ["What was missing", g.missing], ["How to improve", g.improve], ["Ideal answer structure", g.ideal_structure]].map(([t, list]: any) =>
          list?.length ? <div key={t}><h3 className="mb-1 font-semibold">{t}</h3><ul className="list-disc space-y-0.5 pl-5 text-slate-600">{list.map((x: string) => <li key={x}>{x}</li>)}</ul></div> : null)}
      </div>
      {g.invented_claims?.length > 0 && (
        <div className="mt-3"><Notice tone="warn" icon={TriangleAlert}><b>Not on your CV: don't claim this in a real interview:</b> {g.invented_claims.join("; ")}</Notice></div>
      )}
    </Card>
  );
}
