// Recruitment companies: 50 recruiters worth investigating (not a verified list of agencies that hire from India).
// Search + filters, official links, verification labels, your status / notes / follow-up per recruiter, their jobs.
import {
  Bookmark, BookmarkCheck, Building2, ChevronDown, CircleCheck, CircleHelp, ExternalLink, Info, RefreshCw, Search, SearchX, ShieldAlert, UserPlus, X,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Button, Chip, Empty, ErrorText, Field, Notice, PageTitle, Score, SkeletonCard, Tag, buttonClass, formatDate, inputClass } from "../components/ui";
import { useFetch } from "../useFetch";

type Agency = {
  id: number; seed_id: number; name: string; website_url: string; candidate_registration_url: string | null; country: string | null;
  recruitment_category: string; category_label: string; focus: string | null; industry_specializations: string[]; job_family_specializations: string[];
  job_feed: string | null; ingestion: "automatic" | "manual";
  international_recruitment_supported: boolean | null; india_candidate_support_verified: boolean | null;
  visa_sponsorship_support_verified: boolean | null; relocation_support_verified: boolean | null; german_language_requirements: string | null;
  verification_status: string; source_url: string | null; last_verified_at: string | null; verification_note: string | null;
  status: string; is_saved: boolean; notes: string | null; last_contact_at: string | null; next_follow_up: string | null;
  jobs: number; good_matches: number; applied: number;
};

const STATUS_LABEL: Record<string, string> = {
  NOT_REVIEWED: "Not reviewed", REVIEWED: "Reviewed", PROFILE_REGISTERED: "Profile registered", RELEVANT_JOB_FOUND: "Relevant job found",
  APPLICATION_PREPARED: "Application prepared", APPLIED: "Applied", FOLLOW_UP_NEEDED: "Follow-up needed", NO_RELEVANT_OPENINGS: "No relevant openings",
};
const STATUS_TONE: Record<string, string> = {
  NOT_REVIEWED: "bg-neutral-bg text-neutral", REVIEWED: "bg-sky-50 text-sky-700", PROFILE_REGISTERED: "bg-teal-50 text-teal-700",
  RELEVANT_JOB_FOUND: "bg-amber-50 text-amber-800", APPLICATION_PREPARED: "bg-orange-50 text-orange-700", APPLIED: "bg-ok-bg text-ok",
  FOLLOW_UP_NEEDED: "bg-pink-50 text-pink-700", NO_RELEVANT_OPENINGS: "bg-slate-100 text-slate-500",
};
const CATEGORY_TONE: Record<string, string> = {
  india: "bg-orange-50 text-orange-700", staffing: "bg-sky-50 text-sky-700", engineering: "bg-teal-50 text-teal-700", specialist: "bg-rose-50 text-rose-700",
};
const VERIFY: Record<string, { label: string; className: string; icon: typeof CircleCheck }> = {
  unverified: { label: "Not checked yet", className: "bg-neutral-bg text-neutral", icon: CircleHelp },
  website_ok: { label: "Website checked", className: "bg-teal-50 text-teal-700", icon: CircleCheck },
  website_blocked: { label: "Site blocks checks", className: "bg-warn-bg text-warn", icon: ShieldAlert },
  website_unreachable: { label: "Website not reachable", className: "bg-bad-bg text-bad", icon: ShieldAlert },
  confirmed: { label: "Confirmed by you", className: "bg-ok-bg text-ok", icon: CircleCheck },
};
const FACTS = [["india_candidate_support_verified", "Candidates in India"], ["visa_sponsorship_support_verified", "Visa sponsorship"],
  ["relocation_support_verified", "Relocation support"], ["international_recruitment_supported", "International recruitment"]] as const;
const dateInput = (iso: string | null) => (iso ? iso.slice(0, 10) : "");

export default function Agencies() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [industry, setIndustry] = useState("");
  const [family, setFamily] = useState("");
  const [country, setCountry] = useState("");
  const [status, setStatus] = useState("");
  const [saved, setSaved] = useState(false);
  const [sort, setSort] = useState("jobs");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const { data: options } = useFetch<any>("/api/agencies/options");
  const params = new URLSearchParams({ q, category, industry, family, country, status, sort, ...(saved ? { saved: "true" } : {}) });
  const { data, error, loading, reload } = useFetch<{ total: number; items: Agency[] }>(`/api/agencies?${params}`);
  const filtered = !!(q || category || industry || family || country || status || saved);

  async function checkWebsites() {
    setBusy(true);
    setMessage("Opening the official websites one by one (about 2 seconds each)…");
    try {
      let checked = 0, ok = 0;
      const problems: string[] = [];
      for (let round = 0; round < 3; round++) {  // each call runs ≤ ~100 s, so this also works on Vercel
        const r = await api("/api/agencies/check-websites", { method: "POST" });
        checked += r.checked; ok += r.ok; problems.push(...r.problems.map((p: any) => `${p.name}: ${p.note}`));
        setMessage(`Checked ${checked} websites…`);
        if (checked >= 50 || !r.checked) break;
      }
      setMessage(`Checked ${checked} websites: ${ok} answered${problems.length ? `. Needs a look: ${problems.join(" · ")}` : ""}.`);
      reload();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function clear() {
    setQ(""); setCategory(""); setIndustry(""); setFamily(""); setCountry(""); setStatus(""); setSaved(false);
  }

  return (
    <div className="space-y-5">
      <PageTitle title="Recruitment companies" subtitle="Recruiters to investigate for jobs in Germany: track who you contacted, what they offer, and their jobs."
        right={<Button icon={RefreshCw} loading={busy} onClick={checkWebsites}>Check websites</Button>} />
      <Notice icon={Info}>
        This list is a starting point, not proof that an agency accepts applicants from India or sponsors visas. “Website checked” only means the
        official site answered. Mark India / visa / relocation support as confirmed only with the page that says so. The app never contacts recruiters
        or sends your CV.
      </Notice>
      {message && <Notice icon={Info}>{message}</Notice>}

      <section className="space-y-3 rounded-card border border-line bg-surface p-4 shadow-card">
        <div className="flex flex-col gap-2 md:flex-row">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search recruitment companies</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input className={`${inputClass} pl-9`} placeholder="Company name or focus (SAP, automotive, fintech…)" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:flex">
            <select aria-label="Job family" className={`${inputClass} md:w-44`} value={family} onChange={(e) => setFamily(e.target.value)}>
              <option value="">All job families</option>
              {options?.job_families.map((f: string) => <option key={f}>{f}</option>)}
            </select>
            <select aria-label="Location" className={`${inputClass} md:w-32`} value={country} onChange={(e) => setCountry(e.target.value)}>
              <option value="">All locations</option>
              {options?.countries.map((c: string) => <option key={c}>{c}</option>)}
            </select>
            <select aria-label="Your status" className={`${inputClass} md:w-44`} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Any status</option>
              {options?.statuses.map((s: string) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </select>
            <select aria-label="Sort" className={`${inputClass} md:w-40`} value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="jobs">Most matches</option><option value="name">Name A–Z</option><option value="status">By status</option><option value="id">List order</option>
            </select>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip on={!category} onClick={() => setCategory("")}>All categories</Chip>
          {options && Object.entries(options.categories).map(([k, label]) => (
            <Chip key={k} on={category === k} onClick={() => setCategory(category === k ? "" : k)}>{label as string}</Chip>
          ))}
          <Chip on={saved} onClick={() => setSaved(!saved)}>Saved only</Chip>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted">Industry:</span>
          {options?.industries.map((i: string) => <Chip key={i} on={industry === i} onClick={() => setIndustry(industry === i ? "" : i)}>{i}</Chip>)}
        </div>
        {filtered && <button onClick={clear} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"><X className="size-3.5" /> Clear filters</button>}
      </section>

      <ErrorText error={error} />
      {loading && !data ? (
        <div className="grid gap-4 md:grid-cols-2"><SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
      ) : !data?.items.length ? (
        <Empty icon={SearchX} title="No recruitment company matches" text="Try fewer filters." action={<Button onClick={clear}>Clear filters</Button>} />
      ) : (
        <>
          <p className="text-sm text-muted">{data.total} of 50 recruitment companies</p>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((a) => <AgencyCard key={a.id} a={a} statuses={options?.statuses ?? []} onChange={reload} />)}
          </div>
        </>
      )}
    </div>
  );
}

function AgencyCard({ a, statuses, onChange }: { a: Agency; statuses: string[]; onChange: () => void }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const v = VERIFY[a.verification_status] ?? VERIFY.unverified;

  async function patch(body: object) {
    try { setError(null); await api(`/api/agencies/${a.id}`, { method: "PATCH", body }); onChange(); } catch (e) { setError((e as Error).message); }
  }

  return (
    <article className="flex min-w-0 flex-col rounded-card border border-line bg-surface p-4 shadow-card transition hover:shadow-lift">
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-control bg-amber-50 text-amber-700"><Building2 className="size-5" aria-hidden /></span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold leading-snug text-ink">{a.name}</h2>
          <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${CATEGORY_TONE[a.recruitment_category] ?? ""}`}>{a.category_label}</span>
        </div>
        <button onClick={() => patch({ is_saved: !a.is_saved })} aria-pressed={a.is_saved} aria-label={a.is_saved ? `Remove ${a.name} from saved` : `Save ${a.name}`}
          className={`rounded-control p-1.5 hover:bg-canvas ${a.is_saved ? "text-primary" : "text-slate-400 hover:text-ink"}`}>
          {a.is_saved ? <BookmarkCheck className="size-[18px]" /> : <Bookmark className="size-[18px]" />}
        </button>
      </div>
      <p className="mt-3 text-sm text-slate-600">{a.focus}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {a.industry_specializations.map((i) => <span key={i} className="rounded-full bg-canvas px-2 py-0.5 text-[11px] text-muted">{i}</span>)}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
        <Tag color={v.className} icon={v.icon}>{v.label}{a.last_verified_at ? ` · ${formatDate(a.last_verified_at)}` : ""}</Tag>
        <Tag color={a.ingestion === "automatic" ? "bg-teal-50 text-teal-700" : "bg-neutral-bg text-neutral"}>Jobs: {a.ingestion === "automatic" ? "read automatically" : "manual"}</Tag>
        {a.country && a.country !== "Germany" && <Tag>{a.country}</Tag>}
      </div>
      {a.jobs > 0 && (
        <Link to={`/jobs?agency=${encodeURIComponent(a.name)}`} className="mt-2 text-sm font-medium text-primary hover:underline">
          {a.jobs} open job{a.jobs === 1 ? "" : "s"} · {a.good_matches} good match{a.good_matches === 1 ? "" : "es"}{a.applied ? ` · ${a.applied} applied` : ""} →
        </Link>
      )}

      <div className="mt-auto space-y-3 pt-4">
        <label className="block"><span className="sr-only">Your status with {a.name}</span>
          <select value={a.status} onChange={(e) => patch({ status: e.target.value, last_contact_at: ["PROFILE_REGISTERED", "APPLIED"].includes(e.target.value) ? new Date().toISOString() : undefined })}
            className={`w-full rounded-control border-0 px-3 py-2 text-sm font-medium ring-1 ring-line ${STATUS_TONE[a.status] ?? ""}`}>
            {statuses.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </label>
        <div className="flex flex-wrap gap-2">
          <a href={a.website_url} target="_blank" rel="noreferrer" className={buttonClass("normal")}><ExternalLink className="size-4" aria-hidden /> Website</a>
          {a.candidate_registration_url && (
            <a href={a.candidate_registration_url} target="_blank" rel="noreferrer" className={buttonClass("primary")}><UserPlus className="size-4" aria-hidden /> Candidate page</a>
          )}
          <Button kind="ghost" onClick={() => setOpen(!open)}>
            <ChevronDown className={`size-4 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden /> {open ? "Less" : "Details"}
          </Button>
        </div>
        <ErrorText error={error} />
        {open && <Details a={a} patch={patch} />}
      </div>
    </article>
  );
}

function Details({ a, patch }: { a: Agency; patch: (body: object) => Promise<void> }) {
  const { data: jobs } = useFetch<any[]>(a.jobs ? `/api/agencies/${a.id}/jobs` : null);
  const [facts, setFacts] = useState<Record<string, boolean>>({});
  const [source, setSource] = useState("");
  const confirm = async (e: FormEvent) => {
    e.preventDefault();
    await patch({ ...Object.fromEntries(Object.entries(facts).filter(([, on]) => on)), source_url: source });
    setFacts({}); setSource("");
  };
  return (
    <div className="space-y-4 border-t border-line pt-3 text-sm">
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        {FACTS.map(([key, label]) => (
          <div key={key} className="contents">
            <dt className="text-muted">{label}</dt>
            <dd className={a[key] ? "font-medium text-ok" : "text-muted"}>{a[key] ? "Confirmed" : "Not verified"}</dd>
          </div>
        ))}
        <dt className="text-muted">German needed</dt><dd className="text-muted">{a.german_language_requirements ?? "Not verified"}</dd>
        <dt className="text-muted">Last check</dt>
        <dd className="text-muted">{a.verification_note ?? "–"}{a.source_url && a.verification_status === "confirmed" && <> · <a href={a.source_url} target="_blank" rel="noreferrer" className="text-primary underline">source</a></>}</dd>
      </dl>

      <div className="grid grid-cols-2 gap-2">
        <Field label="Last contact"><input type="date" className={`${inputClass} h-9 py-1`} defaultValue={dateInput(a.last_contact_at)}
          onBlur={(e) => e.target.value !== dateInput(a.last_contact_at) && patch({ last_contact_at: e.target.value ? new Date(e.target.value).toISOString() : null })} /></Field>
        <Field label="Follow up on"><input type="date" className={`${inputClass} h-9 py-1`} defaultValue={dateInput(a.next_follow_up)}
          onBlur={(e) => e.target.value !== dateInput(a.next_follow_up) && patch(e.target.value ? { next_follow_up: new Date(e.target.value).toISOString() } : { clear_follow_up: true })} /></Field>
      </div>
      <Field label="Notes (who you spoke to, what they said…)">
        <textarea rows={3} className={inputClass} defaultValue={a.notes ?? ""} onBlur={(e) => e.target.value !== (a.notes ?? "") && patch({ notes: e.target.value })} />
      </Field>

      <form onSubmit={confirm} className="space-y-2 rounded-control bg-canvas p-3">
        <p className="text-xs font-semibold text-ink">Confirm what you verified</p>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {FACTS.map(([key, label]) => (
            <label key={key} className="inline-flex items-center gap-1.5 text-xs">
              <input type="checkbox" checked={!!facts[key]} onChange={(e) => setFacts({ ...facts, [key]: e.target.checked })} /> {label}
            </label>
          ))}
        </div>
        <input type="url" required pattern="https://.*" className={`${inputClass} h-9 py-1 text-xs`} placeholder="https://… page that says so"
          value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source page" />
        <Button type="submit" disabled={!Object.values(facts).some(Boolean)}>Save with source</Button>
      </form>

      {!!jobs?.length && (
        <div>
          <p className="mb-1 text-xs font-semibold text-ink">Their jobs (best match first)</p>
          <ul className="divide-y divide-line">
            {jobs.slice(0, 6).map((j) => (
              <li key={j.id} className="flex items-center gap-2 py-1.5">
                <Score value={j.score} />
                <Link to={`/jobs/${j.id}`} className="min-w-0 flex-1 truncate text-xs font-medium text-ink hover:text-primary">{j.title}</Link>
                <span className="shrink-0 text-[11px] text-muted">{j.location}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
