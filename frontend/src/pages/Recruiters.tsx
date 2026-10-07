// Find the right recruiter yourself (search links) and send a ready-made pitch yourself.
import { ExternalLink, Lightbulb, Mail, MapPin, MessageSquare, PenLine, UserSearch, Users } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Button, Card, Chip, CompanyAvatar, CopyButton, Empty, Field, Notice, PageTitle, Score, SkeletonCard, StatusBadge, inputClass } from "../components/ui";
import { useFetch } from "../useFetch";

type Pitch = { note: string; note_length: number; message: string; email_subject: string; email_body: string };

function PitchPart({ title, icon: Icon, copy, children }: { title: ReactNode; icon: typeof Mail; copy: string; children: ReactNode }) {
  return (
    <div className="rounded-control border border-ai-100 bg-surface p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <b className="inline-flex items-center gap-2 text-sm"><Icon className="size-4 text-ai" aria-hidden />{title}</b>
        <CopyButton text={copy} />
      </div>
      <p className="whitespace-pre-wrap break-words text-sm text-slate-700">{children}</p>
    </div>
  );
}

export default function Recruiters() {
  const [city, setCity] = useState<string | null>(null);
  const { data } = useFetch(`/api/recruiters${city ? `?city=${city}` : ""}`);
  const [open, setOpen] = useState<{ jobId: number; pitch: Pitch } | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [name, setName] = useState("");

  async function makePitch(jobId: number) {
    setBusy(jobId);
    try {
      setOpen({ jobId, pitch: await api(`/api/jobs/${jobId}/pitch`, { body: { contact_name: name || null } }) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      <PageTitle title="Recruiters" subtitle="Companies with good jobs for you. Open a search link to find their recruiter, then send the pitch yourself." />

      <div className="flex flex-wrap gap-2" role="group" aria-label="City">
        <Chip on={city === null} onClick={() => setCity(null)}>All Germany</Chip>
        {(data?.cities ?? []).map((c: string) => <Chip key={c} on={city === c} onClick={() => setCity(c)}>{c}</Chip>)}
      </div>

      <Card>
        <div className="grid gap-4 md:grid-cols-2 md:items-start">
          <Field label="Recruiter's name (optional, makes the pitch personal)">
            <input className={inputClass} placeholder="e.g. Anna Schmidt" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Notice icon={Lightbulb}>
            Send a connection request with the short note (LinkedIn allows 300 characters), and the longer message after they accept.
            Pitch 5–10 people a day: personal beats mass messages.
          </Notice>
        </div>
      </Card>

      {!data ? <div className="grid gap-4 lg:grid-cols-2"><SkeletonCard lines={4} /><SkeletonCard lines={4} /></div>
        : !data.companies?.length ? <Empty icon={UserSearch} title="No companies here yet" text="No good or near-good jobs in this city yet. Try “All Germany”." />
        : (
          <div className="grid gap-4 lg:grid-cols-2">
            {data.companies.map((c: any) => (
              <Card key={c.company} title={<span className="flex items-center gap-3"><CompanyAvatar name={c.company} />{c.company}</span>}>
                <div className="mb-3 flex flex-wrap gap-2">
                  {Object.entries(c.links).map(([label, url]) => (
                    <a key={label} href={url as string} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-full border border-line px-2.5 py-1 text-xs font-medium text-primary hover:border-primary/40 hover:bg-primary-50">
                      <Users className="size-3.5" aria-hidden />{label}<ExternalLink className="size-3" aria-hidden />
                    </a>
                  ))}
                </div>
                <ul className="divide-y divide-line">
                  {c.jobs.map((j: any) => (
                    <li key={j.id} className="py-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <Link to={`/jobs/${j.id}`} className="text-sm font-semibold text-ink hover:text-primary">{j.title}</Link>
                          <div className="mt-0.5 inline-flex items-center gap-1 text-xs text-muted"><MapPin className="size-3.5" />{j.location}</div>
                        </div>
                        <span className="flex flex-wrap items-center gap-2">
                          {j.applied && <StatusBadge status="APPLIED" />}
                          <Score value={j.score} />
                          <Button kind="ai" icon={PenLine} loading={busy === j.id} onClick={() => makePitch(j.id)}>Write pitch</Button>
                        </span>
                      </div>

                      {open && open.jobId === j.id && (
                        <div className="mt-3 space-y-3 rounded-control bg-ai-50 p-3">
                          <PitchPart title={`LinkedIn note (${open.pitch.note_length}/300)`} icon={MessageSquare} copy={open.pitch.note}>{open.pitch.note}</PitchPart>
                          <PitchPart title="LinkedIn message (after they accept)" icon={MessageSquare} copy={open.pitch.message}>{open.pitch.message}</PitchPart>
                          <PitchPart title={`Email: ${open.pitch.email_subject}`} icon={Mail} copy={`${open.pitch.email_subject}\n\n${open.pitch.email_body}`}>{open.pitch.email_body}</PitchPart>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        )}
    </div>
  );
}
