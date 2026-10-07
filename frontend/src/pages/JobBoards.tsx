// All job platforms in one place: which ones the app reads by itself, and one-click searches for the rest.
import { Building2, ExternalLink, Globe, Info, MapPinned, Search, Zap } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, Notice, PageTitle, Pill, SkeletonCard, inputClass } from "../components/ui";
import { useFetch } from "../useFetch";

const GROUP_ICON: Record<string, typeof Globe> = { Germany: Globe, Europe: Globe, "Direct employers": Building2 };

export default function JobBoards() {
  const [q, setQ] = useState<string | null>(null);
  const { data } = useFetch(`/api/job-boards${q ? `?q=${encodeURIComponent(q)}` : ""}`);

  return (
    <div className="space-y-5">
      <PageTitle title="Job boards" subtitle="Automatic sources are read by the app every day. The others have no public API or forbid bots: open the search yourself." />

      <Card>
        <div className="grid gap-4 md:grid-cols-[minmax(0,320px)_1fr] md:items-end">
          <label className="block text-sm">
            <span className="mb-1.5 block text-[13px] font-medium text-slate-700">Search keyword</span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
              <select className={`${inputClass} pl-9`} value={data?.keyword ?? ""} onChange={(e) => setQ(e.target.value)}>
                {(data?.keywords ?? []).map((k: string) => <option key={k}>{k}</option>)}
              </select>
            </span>
          </label>
          <Notice icon={Info}>
            Found a job on one of these sites? <Link to="/jobs" className="font-medium text-primary hover:underline">Jobs → Import job</Link> and paste the description, so it is saved and scored.
          </Notice>
        </div>
      </Card>

      {!data && <div className="space-y-3"><SkeletonCard lines={5} /><SkeletonCard lines={5} /></div>}
      {data?.groups?.map((g: any) => (
        <Card key={g.group} title={g.group} icon={GROUP_ICON[g.group] ?? MapPinned}
          subtitle={`${g.boards.filter((b: any) => b.kind === "automatic").length} automatic · ${g.boards.length} total`}>
          <ul className="-mx-2 divide-y divide-line">
            {g.boards.map((b: any) => (
              <li key={b.name} className="flex flex-col gap-3 rounded-control px-2 py-3 transition-colors hover:bg-canvas sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 font-medium text-ink">
                    {b.name}
                    {b.kind === "automatic" && <Pill className="bg-ok-bg text-ok" icon={Zap}>Automatic</Pill>}
                    {b.kind === "off" && <Pill className="bg-neutral-bg text-neutral">Off · enable in Settings</Pill>}
                  </div>
                  <div className="mt-0.5 text-[13px] text-muted">{b.why}</div>
                </div>
                {b.url && (
                  <a href={b.url} target="_blank" rel="noreferrer"
                    className="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-control border border-line bg-surface px-3 py-2 text-sm font-medium text-primary transition-colors hover:border-primary/40 hover:bg-primary-50">
                    <span className="max-w-[220px] truncate">Search “{data.keyword}”</span><ExternalLink className="size-3.5 shrink-0" aria-hidden />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </div>
  );
}
