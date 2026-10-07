// Your profile (the only source of truth for answers) and app settings.
import { useEffect, useState } from "react";

import { api } from "../api";
import { CircleCheck, Gauge, Globe, ListChecks, RefreshCw, Save, TriangleAlert, UserRound } from "lucide-react";

import { Button, Card, ErrorText, Field, Notice, PageTitle, SkeletonPage, inputClass } from "../components/ui";
import { useFetch } from "../useFetch";

const lines = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);

function YesNo({ label, value, onChange }: { label: string; value: boolean | null; onChange: (v: boolean | null) => void }) {
  return (
    <Field label={label}>
      <select className={inputClass} value={value === null ? "" : value ? "yes" : "no"} onChange={(e) => onChange(e.target.value === "" ? null : e.target.value === "yes")}>
        <option value="">Not set (you will be asked)</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    </Field>
  );
}

export default function Settings() {
  const { data: loadedProfile } = useFetch("/api/profile");
  const { data: loadedSettings } = useFetch("/api/settings");
  const { data: info } = useFetch<{ mode: string }>("/api/info");
  const [p, setP] = useState<any>(null);
  const [s, setS] = useState<any>(null);
  const [skills, setSkills] = useState("");
  const [german, setGerman] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (loadedProfile && !p) {
      setP(loadedProfile);
      setSkills(loadedProfile.skills.map((x: any) => (x.years != null ? `${x.name}: ${x.years}` : x.name)).join("\n"));
      setGerman(loadedProfile.languages.find((l: any) => l.language === "German")?.level ?? "");
    }
  }, [loadedProfile, p]);
  useEffect(() => {
    if (loadedSettings && !s) setS(loadedSettings);
  }, [loadedSettings, s]);

  async function save(what: "profile" | "settings", button: string = what) {
    try {
      setError(null);
      setBusy(button);
      if (what === "profile") {
        const skillList = lines(skills).map((l) => {
          const [name, years] = l.split(":").map((x) => x.trim());
          return { name, years: years ? Number(years) : null };
        });
        const languages = [...p.languages.filter((l: any) => l.language !== "German"), ...(german ? [{ language: "German", level: german }] : [])];
        const { missing_facts, id, user_id, ...fields } = p;
        setP(await api("/api/profile", { method: "PATCH", body: { ...fields, education: lines(p.education.join("\n")), target_roles: lines(p.target_roles.join("\n")), skills: skillList, languages } }));
      } else {
        // lists keep empty lines while you type; drop them when saving
        const clean = Object.fromEntries(Object.entries(s).map(([k, v]) => [k, Array.isArray(v) ? lines(v.join("\n")) : v]));
        setS(await api("/api/settings", { method: "PATCH", body: clean }));
      }
      setMessage("Saved");
      setTimeout(() => setMessage(null), 2500);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (!p || !s) return <SkeletonPage />;
  const text = (key: string, label: string, type = "text") => (
    <Field label={label}>
      <input type={type} className={inputClass} value={p[key] ?? ""} onChange={(e) => setP({ ...p, [key]: type === "number" ? Number(e.target.value) : e.target.value || null })} />
    </Field>
  );
  const list = (key: string, label: string) => (
    <Field label={label}>
      <textarea rows={5} className={`${inputClass} font-mono text-[13px]`} value={s[key].join("\n")} onChange={(e) => setS({ ...s, [key]: e.target.value.split("\n") })} />
    </Field>
  );

  return (
    <div className="space-y-5">
      <PageTitle title="Settings" subtitle="Your profile (from your CV), the roles to search, and how the automation works."
        right={message && <span role="status" className="inline-flex items-center gap-1.5 rounded-full bg-ok-bg px-3 py-1.5 text-sm font-medium text-ok"><CircleCheck className="size-4" aria-hidden />{message}</span>} />
      <ErrorText error={error} />

      <Card title="Job roles to search" subtitle="Every source searches only these roles" icon={ListChecks}
        right={<Button kind="primary" icon={Save} loading={busy === "roles"} onClick={() => save("settings", "roles")}>Save roles</Button>}>
        <Field label="One role per line. Every source searches only these roles (the automation, Search now and Job boards use them).">
          <textarea rows={8} className={inputClass} placeholder={"Data Analyst\nBI Developer"} value={s.search_queries.join("\n")} onChange={(e) => setS({ ...s, search_queries: e.target.value.split("\n") })} />
        </Field>
        <p className="mt-2 text-xs leading-relaxed text-muted">
          A job is kept when its title has a real word of a role ("Data" in "Data Analyst"; words like engineer, developer or manager alone don't count).
          These roles also count as target roles in the match score. After changing them, press "Re-score all jobs" below.
          New install? Put them in .env as JOB_KEYWORDS=Data Analyst, BI Developer.
        </p>
      </Card>

      <Card title="My profile" subtitle="Used for the score, tailored CV and cover letter" icon={UserRound}
        right={<Button kind="primary" icon={Save} loading={busy === "profile"} onClick={() => save("profile")}>Save profile</Button>}>
        {p.missing_facts.length > 0 && <div className="mb-4"><Notice tone="warn" icon={TriangleAlert}>Still missing: {p.missing_facts.join(", ")}</Notice></div>}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {text("name", "Name")}
          {text("location", "Where I live now")}
          {text("years_experience", "Years of experience", "number")}
          {text("email", "Email", "email")}
          {text("phone", "Phone")}
          {text("linkedin_url", "LinkedIn link")}
          {text("github_url", "GitHub link")}
          {text("headline", "Headline")}
          <YesNo label="I need visa sponsorship for Germany" value={p.visa_required} onChange={(v) => setP({ ...p, visa_required: v })} />
          <Field label="German level (empty = none)"><input className={inputClass} placeholder="A2, B1, B2, C1…" value={german} onChange={(e) => setGerman(e.target.value)} /></Field>
          <Field label="Skills (one per line, 'Python: 2.5' = years)">
            <textarea rows={10} className={inputClass} value={skills} onChange={(e) => setSkills(e.target.value)} />
          </Field>
          <div className="sm:col-span-2 lg:col-span-3">
            <Field label="Summary (from your CV)">
              <textarea rows={3} className={inputClass} value={p.summary ?? ""} onChange={(e) => setP({ ...p, summary: e.target.value })} />
            </Field>
          </div>
          <Field label="Education (one per line)">
            <textarea rows={3} className={inputClass} value={p.education.join("\n")} onChange={(e) => setP({ ...p, education: e.target.value.split("\n") })} />
          </Field>
          <div className="sm:col-span-2">
            <p className="mb-1.5 text-[13px] font-medium text-slate-700">Experience (from your CV)</p>
            <ul className="space-y-2 text-sm">
              {p.experience.map((x: any) => (
                <li key={x.company} className="rounded-control border border-line bg-canvas px-3 py-2">
                  <b className="font-semibold">{x.role}</b><span className="block text-xs text-muted">{x.company} · {x.dates}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="sm:col-span-2">
            <Field label="Job titles I want (one per line)">
              <textarea rows={10} className={inputClass} value={p.target_roles.join("\n")} onChange={(e) => setP({ ...p, target_roles: e.target.value.split("\n") })} />
            </Field>
          </div>
        </div>
      </Card>

      <Card title="Score and automation" subtitle="Match threshold, daily start and score weights" icon={Gauge} right={
        <>
          <Button icon={RefreshCw} loading={busy === "rescore"} onClick={async () => {
            setBusy("rescore");
            try {
              const r = await api("/api/jobs/rescore-all", { method: "POST" });
              setMessage(`Re-scored ${r.rescored} jobs · ${r.matching} matching`);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(null);
            }
          }}>Re-score all jobs</Button>
          <Button kind="primary" icon={Save} loading={busy === "score"} onClick={() => save("settings", "score")}>Save settings</Button>
        </>
      }>
        <div className="grid gap-4 sm:grid-cols-3">
          {[["min_score", "Minimum match score"], ["max_runtime_hours", "Automation hours (≤ 6)"], ["repeat_every_minutes", "Search again every (minutes)"]].map(([key, label]) => (
            <Field key={key} label={label}>
              <input type="number" className={inputClass} value={s[key]} onChange={(e) => setS({ ...s, [key]: Number(e.target.value) })} />
            </Field>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap items-end gap-4 rounded-control border border-line bg-canvas p-4">
          <label className="flex min-h-10 items-center gap-2.5 text-sm font-medium">
            <input type="checkbox" className="size-4 accent-[var(--color-primary)]" checked={!!s.daily_auto_start} onChange={(e) => setS({ ...s, daily_auto_start: e.target.checked })} />
            Start the automation by itself every day
          </label>
          <Field label="at (your computer's time)">
            <input type="time" className={inputClass} value={s.daily_start_time} onChange={(e) => setS({ ...s, daily_start_time: e.target.value })} />
          </Field>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted">
          {info?.mode === "serverless"
            ? "On Vercel the daily run is started by Vercel Cron (times in vercel.json, UTC), not by this time. The switch above still turns it on or off."
            : "The backend must be running (./start.sh). If the computer was off at that time, it starts as soon as the backend runs again that day."}
        </p>
        <h3 className="mb-3 mt-5 text-sm font-semibold">Score weights</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Object.entries(s.weights).map(([key, value]) => (
            <Field key={key} label={key.charAt(0).toUpperCase() + key.slice(1)}>
              <input type="number" className={inputClass} value={value as number} onChange={(e) => setS({ ...s, weights: { ...s.weights, [key]: Number(e.target.value) } })} />
            </Field>
          ))}
        </div>
      </Card>

      <Card title="Where to search" subtitle="Sources and the companies whose careers pages are read" icon={Globe}
        right={<Button kind="primary" icon={Save} loading={busy === "where"} onClick={() => save("settings", "where")}>Save</Button>}>
        <div className="grid gap-4 md:grid-cols-2">
          {list("sources", "Automatic sources (greenhouse, lever, smartrecruiters, personio, ashby, arbeitnow, berlinstartupjobs, munichstartup, startupcityhamburg, demo)")}
          {list("greenhouse_boards", "Greenhouse companies (boards.greenhouse.io/NAME)")}
          {list("lever_companies", "Lever companies (jobs.lever.co/NAME)")}
          {list("smartrecruiters_companies", "SmartRecruiters companies (jobs.smartrecruiters.com/NAME)")}
          {list("personio_companies", "Personio companies (NAME.jobs.personio.de)")}
          {list("ashby_boards", "Ashby companies (jobs.ashbyhq.com/NAME)")}
        </div>
      </Card>
    </div>
  );
}
