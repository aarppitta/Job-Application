// Pieces used by the job analysis, interview and strategy pages.
import { ChevronDown, CircleCheck, CirclePlay, CircleX, Clock, ExternalLink, Flag, RefreshCw, Sparkles } from "lucide-react";
import { useState, type ReactNode } from "react";

import { api } from "../api";
import { DECISION, FACT_STATUS, LEVEL_LOOK, REQ_STATUS } from "../theme";
import { Button, CopyButton, Pill, ProgressBar } from "./ui";

const host = (url: string) => { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; } };

export type Req = { item: string; status: string; why: string };

export function ReqPill({ status }: { status: string }) {
  return <Pill look={REQ_STATUS[status] ?? REQ_STATUS.not_relevant} />;
}

export function LevelPill({ level, prefix }: { level: string; prefix?: string }) {
  const key = Object.keys(LEVEL_LOOK).find((k) => level?.startsWith(k)) ?? "Medium";
  return <Pill className={LEVEL_LOOK[key]}>{prefix ? `${prefix}: ` : ""}{level}</Pill>;
}

/** DSA requirement: higher = harder for you, so the colors run the other way (Low–Medium green … Very High red). */
const DSA_LOOK: Record<string, string> = {
  "Low–Medium": "bg-ok-bg text-ok", Low: "bg-ok-bg text-ok", None: "bg-ok-bg text-ok", Medium: "bg-info-bg text-info",
  "Medium–High": "bg-warn-bg text-warn", High: "bg-warn-bg text-warn", "Very High": "bg-bad-bg text-bad",
};
export function DsaPill({ level, prefix }: { level: string; prefix?: string }) {
  return <Pill className={DSA_LOOK[level] ?? "bg-neutral-bg text-neutral"}>{prefix ? `${prefix}: ` : ""}{level}</Pill>;
}

/** One group of JD requirements compared with your CV. */
export function RequirementGroup({ title, items, empty = "None in the JD" }: { title: string; items: Req[]; empty?: string }) {
  return (
    <div className="min-w-0">
      <h3 className="mb-2 text-sm font-semibold text-ink">{title} <span className="font-normal text-muted">({items.length})</span></h3>
      {items.length ? (
        <ul className="divide-y divide-line rounded-control border border-line">
          {items.map((r) => (
            <li key={r.item} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-3 py-2 text-sm">
              <span className="min-w-0">
                <span className="font-medium text-ink">{r.item}</span>
                <span className="block text-xs text-muted">{r.why}</span>
              </span>
              <ReqPill status={r.status} />
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-muted">{empty}</p>}
    </div>
  );
}

/** Where a fact comes from: status pill + link + date + confidence. */
export function SourceLine({ status, url, type, date, confidence }: { status?: string; url?: string; type?: string; date?: string; confidence?: string }) {
  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
      {status && <Pill look={FACT_STATUS[status] ?? FACT_STATUS.estimated} />}
      {url ? (
        <a href={url} target="_blank" rel="noreferrer" className="inline-flex max-w-[260px] items-center gap-1 text-primary hover:underline">
          <span className="truncate">{type || host(url)}</span><ExternalLink className="size-3 shrink-0" aria-hidden />
        </a>
      ) : status && status !== "not_found" ? <span>no source</span> : null}
      {date && date !== "unknown" && <span>· {date}</span>}
      {confidence && <span>· {confidence} confidence</span>}
    </span>
  );
}

export function Decision({ rec }: { rec: any }) {
  const look = DECISION[rec.decision] ?? DECISION.SKIP;
  const facts: [string, ReactNode][] = [
    ["Match", `${rec.match}%`], ["CV shortlist", <LevelPill key="s" level={rec.shortlist} />], ["Visa", rec.visa], ["German", rec.german],
    ["DSA", rec.dsa], ["Biggest skill gap", rec.biggest_gap], ["Biggest risk", rec.biggest_risk], ["Preparation", rec.preparation],
    ["Recommended CV", rec.cv], ["Recommended contact", rec.contact],
  ];
  return (
    <section className={`rounded-card border p-5 shadow-card sm:p-6 ${look.ring}`} aria-label="Final recommendation">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`inline-flex items-center gap-2 rounded-control px-3 py-1.5 text-sm font-bold tracking-wide ${look.className}`}>
          <Flag className="size-4" aria-hidden />{rec.label}
        </span>
        <span className="text-sm text-muted">Final recommendation (rule-based, from your CV vs this JD)</span>
      </div>
      <dl className="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
        {facts.map(([k, v]) => (
          <div key={k} className="flex min-w-0 justify-between gap-3 border-b border-line/70 py-1.5">
            <dt className="shrink-0 text-muted">{k}</dt><dd className="min-w-0 text-right font-medium text-ink">{v}</dd>
          </div>
        ))}
      </dl>
      <h3 className="mt-4 text-sm font-semibold">Recommended next actions</h3>
      <ol className="mt-2 grid gap-1.5 text-sm sm:grid-cols-2">
        {rec.next_actions.map((a: string, i: number) => (
          <li key={a} className="flex gap-2"><span className="grid size-5 shrink-0 place-items-center rounded-full bg-primary text-[11px] font-bold text-white">{i + 1}</span>{a}</li>
        ))}
      </ol>
    </section>
  );
}

export function ScoreBars({ parts }: { parts: Record<string, number | null> }) {
  return (
    <div className="space-y-2.5">
      {Object.entries(parts).map(([k, v]) => (
        <div key={k} className="text-sm">
          <div className="mb-1 flex justify-between"><span className="text-muted">{k}</span>
            <span className="font-semibold tabular-nums">{v === null || v === undefined ? "Not relevant" : `${Math.round(v)}%`}</span></div>
          {v !== null && v !== undefined && <ProgressBar value={v} tone={v >= 75 ? "ok" : "primary"} label={k} />}
        </div>
      ))}
    </div>
  );
}

export function Checklist({ items }: { items: { label: string; done: boolean; action?: string }[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {items.map((i) => (
        <li key={i.label} className="flex items-start gap-2">
          {i.done ? <CircleCheck className="mt-0.5 size-4 shrink-0 text-ok-strong" aria-label="Done" />
            : <CircleX className="mt-0.5 size-4 shrink-0 text-slate-400" aria-label="Not done" />}
          <span><span className={i.done ? "text-ink" : "text-muted"}>{i.label}</span>
            {!i.done && i.action && <span className="block text-xs text-primary">{i.action}</span>}</span>
        </li>
      ))}
    </ul>
  );
}

/** Tabs that scroll sideways on phones instead of wrapping. */
export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: string; badge?: ReactNode }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      <div role="tablist" className="inline-flex min-w-full gap-1 border-b border-line">
        {tabs.map((t) => (
          <button key={t.id} role="tab" aria-selected={active === t.id} onClick={() => onChange(t.id)}
            className={`-mb-px inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors ${
              active === t.id ? "border-primary text-primary" : "border-transparent text-muted hover:text-ink"}`}>
            {t.label}{t.badge}
          </button>
        ))}
      </div>
    </div>
  );
}

/** How to answer one interview question: checks, length, steps, your CV facts, pitfalls, opening, plus an AI draft. */
export function AnswerGuide({ q, jobId, ai }: { q: any; jobId: string; ai: boolean }) {
  const [draft, setDraft] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const g = q.guide;
  if (!g) return null;

  async function makeDraft() {
    setBusy(true); setError(null);
    try { setDraft(await api(`/api/jobs/${jobId}/answer-draft`, { body: { question: q.question } })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <div className="mt-2 space-y-3 rounded-control border border-line bg-canvas p-3 text-sm">
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs">
        <span><b className="text-ink">They check:</b> <span className="text-muted">{g.checks}</span></span>
        <span className="inline-flex items-center gap-1"><Clock className="size-3.5 text-muted" /><b className="text-ink">Length:</b> <span className="text-muted">{g.length}</span></span>
      </div>
      <ol className="space-y-1.5">
        {g.steps.map((s: any, i: number) => (
          <li key={s.step} className="flex gap-2">
            <span className="grid size-5 shrink-0 place-items-center rounded-full bg-primary text-[11px] font-bold text-white">{i + 1}</span>
            <span><b className="text-ink">{s.step}:</b> <span className="text-slate-600">{s.detail}</span></span>
          </li>
        ))}
      </ol>
      {g.cv_facts.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold text-ok">Use these real facts from your CV</p>
          <ul className="space-y-1 text-xs text-slate-600">{g.cv_facts.map((f: string) => <li key={f} className="flex gap-1.5"><CircleCheck className="mt-0.5 size-3.5 shrink-0 text-ok-strong" />{f}</li>)}</ul>
        </div>
      )}
      <div>
        <p className="mb-1 text-xs font-semibold text-bad">Avoid</p>
        <ul className="space-y-0.5 text-xs text-slate-600">{g.avoid.map((a: string) => <li key={a} className="flex gap-1.5"><CircleX className="mt-0.5 size-3.5 shrink-0 text-bad-strong" />{a}</li>)}</ul>
      </div>
      <p className="rounded-control border border-line bg-surface p-2 text-xs"><b>Possible opening:</b> <span className="italic text-slate-600">“{g.opening}”</span></p>

      {ai ? (
        <div>
          {!draft && <Button kind="ai" icon={Sparkles} loading={busy} onClick={makeDraft}>Draft an answer with AI</Button>}
          {error && <p className="mt-2 text-xs text-bad">{error}</p>}
          {draft && (
            <div className="space-y-2 rounded-control border border-ai-100 bg-ai-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <b className="inline-flex items-center gap-1.5 text-ai"><Sparkles className="size-4" /> AI sample answer</b>
                <span className="flex gap-2"><CopyButton text={draft.draft} /><Button kind="ghost" icon={RefreshCw} loading={busy} onClick={makeDraft}>Again</Button></span>
              </div>
              {draft.warnings.length > 0 && (
                <p className="rounded-control bg-bad-bg p-2 text-xs text-bad"><b>Remove before using, not on your CV:</b> {draft.warnings.join("; ")}</p>
              )}
              <p className="whitespace-pre-wrap text-sm text-slate-700">{draft.draft}</p>
              <p className="text-xs text-muted">{draft.note}</p>
            </div>
          )}
        </div>
      ) : (
        <p className="text-xs text-muted"><Sparkles className="mr-1 inline size-3.5 text-ai" />Add <code>AI_API_KEY</code> to <code>.env</code> to get an AI sample answer built from your CV.</p>
      )}
    </div>
  );
}

/** A question row that opens its answer guide. */
export function QuestionRow({ q, index, jobId, ai }: { q: any; index?: number; jobId: string; ai: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="py-2.5">
      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between">
        <span className="min-w-0 text-sm">{index !== undefined && <span className="mr-2 text-muted">{index}.</span>}{q.question}
          <span className="block text-xs text-muted">{q.category} · {q.why}</span>
          {q.source_url && <SourceLine status="reported" url={q.source_url} confidence={q.confidence} />}</span>
        <span className="flex shrink-0 items-center gap-2"><LevelPill level={q.probability} />
          <button onClick={() => setOpen(!open)} aria-expanded={open} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
            How to answer <ChevronDown className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} /></button></span>
      </div>
      {open && <AnswerGuide q={q} jobId={jobId} ai={ai} />}
    </li>
  );
}

/** "Learn in Hindi" YouTube links (verified channels + a general Hindi search). */
export function HindiLinks({ links, compact = false }: { links?: { channel: string; about: string; url: string }[]; compact?: boolean }) {
  if (!links?.length) return null;
  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${compact ? "" : "mt-2"}`}>
      <span className="text-xs font-medium text-muted">Learn in Hindi:</span>
      {links.map((l) => (
        <a key={l.channel} href={l.url} target="_blank" rel="noreferrer" title={l.about}
          className="inline-flex items-center gap-1 rounded-full border border-red-100 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 hover:border-red-300">
          <CirclePlay className="size-3.5" aria-hidden />{l.channel}
        </a>
      ))}
    </div>
  );
}
