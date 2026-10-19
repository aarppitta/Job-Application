// My CV: the ONE standard CV used for every application. Edit it here (or upload a PDF/Word CV to fill the fields),
// then Save. The apply bot rebuilds its PDF from this automatically before its next run.
import { ArrowDown, ArrowUp, Download, FileUp, Info, Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState, type ChangeEvent } from "react";

import { api, download } from "../api";
import { Button, Card, ErrorText, Field, Notice, PageTitle, SkeletonPage, inputClass } from "../components/ui";
import { useFetch } from "../useFetch";

type Exp = { role: string; company: string; location: string; dates: string; bullets: string[] };
type Proj = { name: string; tech: string; description?: string; skills?: string[]; bullets: string[] };
type Edu = { degree: string; school: string; dates: string };
type CvForm = { headline: string; summary: string; experience: Exp[]; projects: Proj[]; education: Edu[] };

const toEdu = (line: string): Edu => {
  const parts = line.split("|").map((p) => p.trim()).filter(Boolean);
  const dates = parts.find((p) => /\d{4}/.test(p)) ?? "";
  const rest = parts.filter((p) => p !== dates);
  return { degree: rest[0] ?? "", school: rest[1] ?? "", dates };
};
const fromEdu = (e: Edu) => [e.degree, e.school, e.dates].map((x) => x.trim()).filter(Boolean).join(" | ");
const lines = (text: string) => text.split("\n").map((l) => l.replace(/^[\s•▸\-–]+/, "").trim()).filter(Boolean);

function move<T>(list: T[], i: number, by: number): T[] {
  const j = i + by;
  if (j < 0 || j >= list.length) return list;
  const copy = [...list];
  [copy[i], copy[j]] = [copy[j], copy[i]];
  return copy;
}

export default function MyCv() {
  const { data: profile, error, reload } = useFetch<any>("/api/profile");
  const [form, setForm] = useState<CvForm | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [uploadedText, setUploadedText] = useState<string | null>(null);

  useEffect(() => {
    if (profile && !dirty) {
      setForm({
        headline: profile.headline ?? "", summary: profile.summary ?? "",
        experience: profile.experience ?? [], projects: profile.projects ?? [], education: (profile.education ?? []).map(toEdu),
      });
    }
  }, [profile, dirty]);

  if (error) return <ErrorText error={error} />;
  if (!form) return <SkeletonPage />;

  const set = (patch: Partial<CvForm>) => { setForm({ ...form, ...patch }); setDirty(true); };
  const setExp = (i: number, patch: Partial<Exp>) => set({ experience: form.experience.map((e, k) => (k === i ? { ...e, ...patch } : e)) });
  const setProj = (i: number, patch: Partial<Proj>) => set({ projects: form.projects.map((p, k) => (k === i ? { ...p, ...patch } : p)) });
  const setEdu = (i: number, patch: Partial<Edu>) => set({ education: form.education.map((e, k) => (k === i ? { ...e, ...patch } : e)) });

  async function save() {
    setBusy("save"); setSaveError(null);
    try {
      await api("/api/profile", { method: "PATCH", body: { ...form!, education: form!.education.map(fromEdu).filter(Boolean) } });
      setDirty(false); setMessage("Saved. Every new application uses this CV; the apply bot rebuilds its PDF before its next run.");
      reload();
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy("upload"); setSaveError(null); setMessage("Reading your CV…");
    try {
      const content_base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
        reader.onerror = () => reject(new Error("Could not read the file."));
        reader.readAsDataURL(file);
      });
      const r = await api("/api/profile/cv-import", { body: { filename: file.name, content_base64 } });
      setUploadedText(r.text);
      setMessage(r.message);
      if (r.draft) {
        set({ headline: r.draft.headline, summary: r.draft.summary, experience: r.draft.experience, projects: r.draft.projects,
              education: r.draft.education.map(toEdu) });
      }
    } catch (err) {
      setMessage(null); setSaveError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <PageTitle title="My CV" subtitle="The one standard CV sent with every application (German/EU layout). Only facts you write here are used."
        right={
          <>
            <label className={`inline-flex cursor-pointer items-center gap-2 rounded-control border border-line bg-surface px-3.5 py-2 text-sm font-medium text-ink shadow-sm hover:bg-canvas ${busy ? "pointer-events-none opacity-60" : ""}`}>
              <FileUp className="size-4" aria-hidden /> {busy === "upload" ? "Reading…" : "Upload CV (PDF/Word)"}
              <input type="file" accept=".pdf,.docx" className="sr-only" onChange={upload} />
            </label>
            <Button icon={Download} onClick={() => download("/api/cv.docx", "CV.docx")}>Download (.docx)</Button>
            <Button kind="primary" icon={Save} loading={busy === "save"} disabled={!dirty || !!busy} onClick={save}>Save</Button>
          </>
        } />
      {message && <Notice icon={Info}>{message}</Notice>}
      <ErrorText error={saveError} />
      {dirty && <Notice tone="warn" icon={Info}>Unsaved changes. Check them, then click Save.</Notice>}
      {uploadedText && (
        <details className="rounded-card border border-line bg-surface p-4 text-sm shadow-card">
          <summary className="cursor-pointer font-medium">Text read from the uploaded file</summary>
          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs text-muted">{uploadedText}</pre>
        </details>
      )}

      <Card title="Headline and profile">
        <div className="space-y-4">
          <Field label="Headline (under your name)"><input className={inputClass} value={form.headline} onChange={(e) => set({ headline: e.target.value })} /></Field>
          <Field label="Profile / summary"><textarea rows={5} className={inputClass} value={form.summary} onChange={(e) => set({ summary: e.target.value })} /></Field>
        </div>
      </Card>

      <Card title="Professional experience" subtitle="Newest first. One bullet per line."
        right={<Button icon={Plus} onClick={() => set({ experience: [{ role: "", company: "", location: "", dates: "", bullets: [] }, ...form.experience] })}>Add job</Button>}>
        <div className="space-y-5">
          {form.experience.map((e, i) => (
            <fieldset key={i} className="space-y-3 rounded-control border border-line p-3">
              <legend className="px-1 text-sm font-semibold">{e.role || "New job"}</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Role"><input className={inputClass} value={e.role} onChange={(x) => setExp(i, { role: x.target.value })} /></Field>
                <Field label="Company"><input className={inputClass} value={e.company} onChange={(x) => setExp(i, { company: x.target.value })} /></Field>
                <Field label="Location"><input className={inputClass} value={e.location} onChange={(x) => setExp(i, { location: x.target.value })} /></Field>
                <Field label="Dates" hint="e.g. April 2026 – Present"><input className={inputClass} value={e.dates} onChange={(x) => setExp(i, { dates: x.target.value })} /></Field>
              </div>
              <Field label="Bullets"><textarea rows={Math.max(3, e.bullets.length + 1)} className={inputClass} value={e.bullets.join("\n")}
                onChange={(x) => setExp(i, { bullets: x.target.value.split("\n") })} onBlur={(x) => setExp(i, { bullets: lines(x.target.value) })} /></Field>
              <RowActions onUp={() => set({ experience: move(form.experience, i, -1) })} onDown={() => set({ experience: move(form.experience, i, 1) })}
                onDelete={() => set({ experience: form.experience.filter((_, k) => k !== i) })} what={e.role || "this job"} />
            </fieldset>
          ))}
        </div>
      </Card>

      <Card title="Education" subtitle="Newest first."
        right={<Button icon={Plus} onClick={() => set({ education: [{ degree: "", school: "", dates: "" }, ...form.education] })}>Add degree</Button>}>
        <div className="space-y-3">
          {form.education.map((e, i) => (
            <div key={i} className="grid gap-3 rounded-control border border-line p-3 sm:grid-cols-[1fr_1fr_200px]">
              <Field label="Degree"><input className={inputClass} value={e.degree} onChange={(x) => setEdu(i, { degree: x.target.value })} /></Field>
              <Field label="University, city, country"><input className={inputClass} value={e.school} onChange={(x) => setEdu(i, { school: x.target.value })} /></Field>
              <Field label="Dates" hint="January 2022 – January 2023"><input className={inputClass} value={e.dates} onChange={(x) => setEdu(i, { dates: x.target.value })} /></Field>
              <div className="sm:col-span-3">
                <RowActions onUp={() => set({ education: move(form.education, i, -1) })} onDown={() => set({ education: move(form.education, i, 1) })}
                  onDelete={() => set({ education: form.education.filter((_, k) => k !== i) })} what={e.degree || "this degree"} />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Key projects" subtitle="One bullet per line."
        right={<Button icon={Plus} onClick={() => set({ projects: [...form.projects, { name: "", tech: "", bullets: [] }] })}>Add project</Button>}>
        <div className="space-y-5">
          {form.projects.map((p, i) => (
            <fieldset key={i} className="space-y-3 rounded-control border border-line p-3">
              <legend className="px-1 text-sm font-semibold">{p.name || "New project"}</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name"><input className={inputClass} value={p.name} onChange={(x) => setProj(i, { name: x.target.value })} /></Field>
                <Field label="Technologies" hint="Angular · FastAPI · Python"><input className={inputClass} value={p.tech} onChange={(x) => setProj(i, { tech: x.target.value })} /></Field>
              </div>
              <Field label="Bullets"><textarea rows={Math.max(3, p.bullets.length + 1)} className={inputClass} value={p.bullets.join("\n")}
                onChange={(x) => setProj(i, { bullets: x.target.value.split("\n") })} onBlur={(x) => setProj(i, { bullets: lines(x.target.value) })} /></Field>
              <RowActions onUp={() => set({ projects: move(form.projects, i, -1) })} onDown={() => set({ projects: move(form.projects, i, 1) })}
                onDelete={() => set({ projects: form.projects.filter((_, k) => k !== i) })} what={p.name || "this project"} />
            </fieldset>
          ))}
        </div>
      </Card>
      <p className="text-xs text-muted">Contact details, languages, visa need and skills are edited in Settings → My profile.</p>
    </div>
  );
}

function RowActions({ onUp, onDown, onDelete, what }: { onUp: () => void; onDown: () => void; onDelete: () => void; what: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button kind="ghost" icon={ArrowUp} onClick={onUp}>Up</Button>
      <Button kind="ghost" icon={ArrowDown} onClick={onDown}>Down</Button>
      <Button kind="ghost" icon={Trash2} onClick={() => window.confirm(`Remove ${what} from your CV?`) && onDelete()}>Remove</Button>
    </div>
  );
}
