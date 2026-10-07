// Building blocks used by every page. Colors come from the tokens in index.css and the status config in theme.ts.
import { CircleAlert, Copy, Check, Inbox, LoaderCircle, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { APP_STATUS, MATCH_LEVEL, VISA, scoreTone, type Look } from "../theme";

export const inputClass =
  "w-full rounded-control border border-input bg-surface px-3 py-2 text-sm text-ink placeholder:text-slate-400 " +
  "transition-[border-color,box-shadow] duration-150 focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/15 " +
  "disabled:cursor-not-allowed disabled:bg-canvas disabled:text-muted";

export function Card({ title, subtitle, icon: Icon, right, children, ai, className = "" }: {
  title?: ReactNode; subtitle?: ReactNode; icon?: LucideIcon; right?: ReactNode; children: ReactNode; ai?: boolean; className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-card border bg-surface p-4 shadow-card sm:p-5 ${ai ? "border-ai-100" : "border-line"} ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {Icon && (
              <span className={`grid size-9 shrink-0 place-items-center rounded-control ${ai ? "bg-ai-50 text-ai" : "bg-primary-50 text-primary"}`}>
                <Icon className="size-[18px]" aria-hidden />
              </span>
            )}
            <div className="min-w-0">
              {title && <h2 className="text-base font-semibold text-ink sm:text-[17px]">{title}</h2>}
              {subtitle && <p className="text-[13px] text-muted">{subtitle}</p>}
            </div>
          </div>
          {right && <div className="flex flex-wrap items-center gap-2">{right}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

type ButtonKind = "primary" | "normal" | "danger" | "success" | "ai" | "ghost";
const BUTTON: Record<ButtonKind, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover shadow-sm",
  normal: "border border-line bg-surface text-ink hover:bg-canvas hover:border-input",
  danger: "border border-red-200 bg-surface text-bad hover:bg-bad-bg",
  success: "bg-ok-strong text-white hover:bg-ok shadow-sm",
  ai: "bg-ai text-white hover:bg-ai-hover shadow-sm",
  ghost: "text-muted hover:bg-canvas hover:text-ink",
};
export const buttonClass = (kind: ButtonKind = "normal") =>
  "inline-flex items-center justify-center gap-2 rounded-control px-3.5 py-2 text-sm font-medium transition-colors duration-150 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " + BUTTON[kind];

export function Button({ children, onClick, kind = "normal", disabled, loading, icon: Icon, type = "button", title, className = "" }: {
  children?: ReactNode; onClick?: () => void; kind?: ButtonKind; disabled?: boolean; loading?: boolean;
  icon?: LucideIcon; type?: "button" | "submit"; title?: string; className?: string;
}) {
  return (
    <button type={type} onClick={onClick} disabled={disabled || loading} title={title} aria-label={title} className={`${buttonClass(kind)} ${className}`}>
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : Icon && <Icon className="size-4" aria-hidden />}
      {children}
    </button>
  );
}

export function PageTitle({ title, subtitle, right }: { title: ReactNode; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3 sm:mb-6">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-[30px] sm:leading-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {right && <div className="flex flex-wrap gap-2">{right}</div>}
    </div>
  );
}

/** Rounded pill. Pass a Look from theme.ts, or a className + children. */
export function Pill({ look, children, className = "", icon }: { look?: Look; children?: ReactNode; className?: string; icon?: LucideIcon }) {
  const Icon = icon ?? look?.icon;
  return (
    <span className={`inline-flex max-w-full items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${look?.className ?? ""} ${className}`}>
      {Icon && <Icon className="size-3.5 shrink-0" aria-hidden />}
      <span className="truncate">{children ?? look?.label}</span>
    </span>
  );
}

/** Application status: Applied = green ✓, Rejected = red ✕, … (from theme.ts) */
export function StatusBadge({ status }: { status: string }) {
  return <Pill look={APP_STATUS[status] ?? { label: status, className: "bg-neutral-bg text-neutral" }} />;
}

export function Score({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <Pill className="bg-neutral-bg text-neutral">–</Pill>;
  const tone = scoreTone(value);
  return <span className={`inline-flex min-w-10 justify-center rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${tone.bg} ${tone.text}`}>{Math.round(value)}%</span>;
}

/** Circular score: 92% + "Excellent match" */
export function ScoreRing({ value, size = 56, label = false }: { value: number | null; size?: number; label?: boolean }) {
  const v = value ?? 0;
  const tone = scoreTone(v);
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-3">
      <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={value === null ? "Not scored" : `Match score ${Math.round(v)}%`}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-skeleton)" strokeWidth={6} />
          {value !== null && (
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={tone.stroke} strokeWidth={6} strokeLinecap="round"
              strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} className="transition-[stroke-dashoffset] duration-500" />
          )}
        </svg>
        <span className={`absolute inset-0 grid place-items-center font-bold tabular-nums ${size > 70 ? "text-lg" : "text-xs"} ${tone.text}`}>
          {value === null ? "–" : `${Math.round(v)}%`}
        </span>
      </div>
      {label && value !== null && <span className={`text-sm font-semibold ${tone.text}`}>{tone.label}</span>}
    </div>
  );
}

export function Visa({ status }: { status: string }) {
  return <Pill look={VISA[status] ?? VISA.unclear} />;
}

/** "Good match: apply" / "Stretch" / "Not a match: skip" */
export function MatchLabel({ match }: { match?: { level: string; text: string } }) {
  if (!match) return null;
  return <Pill look={MATCH_LEVEL[match.level] ?? MATCH_LEVEL.unknown}>{match.text}</Pill>;
}

export function Tag({ children, color = "bg-neutral-bg text-neutral", icon }: { children: ReactNode; color?: string; icon?: LucideIcon }) {
  return <Pill className={color} icon={icon}>{children}</Pill>;
}

export function Chip({ on, onClick, children, count }: { on: boolean; onClick: () => void; children: ReactNode; count?: number }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors duration-150 ${
        on ? "border-primary bg-primary-50 text-primary" : "border-line bg-surface text-muted hover:border-input hover:text-ink"}`}>
      {children}
      {count !== undefined && <span className={`rounded-full px-1.5 tabular-nums ${on ? "bg-primary text-white" : "bg-canvas"}`}>{count}</span>}
    </button>
  );
}

export function ErrorText({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <p role="alert" className="flex items-start gap-2 rounded-control border border-red-200 bg-bad-bg/60 p-3 text-sm text-bad">
      <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden /> {error}
    </p>
  );
}

export function Notice({ children, tone = "info", icon: Icon }: { children: ReactNode; tone?: "info" | "warn" | "ok" | "ai"; icon?: LucideIcon }) {
  const look = { info: "border-primary-100 bg-primary-50 text-ink", warn: "border-amber-200 bg-warn-bg/70 text-ink",
    ok: "border-green-200 bg-ok-bg/70 text-ink", ai: "border-ai-100 bg-ai-50 text-ink" }[tone];
  return (
    <div className={`flex items-start gap-3 rounded-card border p-3.5 text-sm ${look}`}>
      {Icon && <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Empty state: icon, title, explanation and an optional button. */
export function Empty({ text, title, icon: Icon = Inbox, action }: { text: ReactNode; title?: string; icon?: LucideIcon; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-card border border-dashed border-input bg-surface px-6 py-10 text-center">
      <span className="mb-3 grid size-12 place-items-center rounded-full bg-primary-50 text-primary"><Icon className="size-6" aria-hidden /></span>
      {title && <h3 className="text-base font-semibold text-ink">{title}</h3>}
      <p className="mt-1 max-w-md text-sm text-muted">{text}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-shimmer rounded-control bg-skeleton ${className}`} aria-hidden />;
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3 rounded-card border border-line bg-surface p-5 shadow-card" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: lines }, (_, i) => <Skeleton key={i} className={`h-3 ${i % 2 ? "w-2/3" : "w-full"}`} />)}
    </div>
  );
}

export function SkeletonPage() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-56" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SkeletonCard /><SkeletonCard /><SkeletonCard />
      </div>
      <SkeletonCard lines={6} />
    </div>
  );
}

export function KpiCard({ label, value, icon: Icon, tone = "primary", hint }: {
  label: string; value: ReactNode; icon: LucideIcon; tone?: "primary" | "ok" | "bad" | "violet" | "offer" | "warn" | "ai"; hint?: ReactNode;
}) {
  const tile = { primary: "bg-primary-50 text-primary", ok: "bg-ok-bg text-ok", bad: "bg-bad-bg text-bad", violet: "bg-violet-bg text-violet",
    offer: "bg-offer-bg text-offer", warn: "bg-warn-bg text-warn", ai: "bg-ai-50 text-ai" }[tone];
  return (
    <div className="min-w-0 rounded-card border border-line bg-surface p-4 shadow-card transition-shadow duration-200 hover:shadow-lift">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[13px] font-medium leading-snug text-muted">{label}</p>
        <span className={`grid size-8 shrink-0 place-items-center rounded-control ${tile}`}><Icon className="size-4" aria-hidden /></span>
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums text-ink sm:text-[28px]">{value ?? "–"}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function ProgressBar({ value, tone = "primary", label }: { value: number; tone?: "primary" | "ok" | "ai"; label?: string }) {
  const bar = { primary: "bg-primary", ok: "bg-ok-strong", ai: "bg-ai" }[tone];
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="h-2 overflow-hidden rounded-full bg-skeleton">
        <div className={`h-full rounded-full ${bar} transition-[width] duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/** Small SVG donut with legend. */
export function Donut({ parts, center }: { parts: { label: string; value: number; color: string }[]; center?: ReactNode }) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  const r = 42, c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
      <div className="relative size-32 shrink-0">
        <svg viewBox="0 0 100 100" className="size-32 -rotate-90" role="img" aria-label={parts.map((p) => `${p.label} ${p.value}`).join(", ")}>
          <circle cx="50" cy="50" r={r} fill="none" stroke="var(--color-skeleton)" strokeWidth="12" />
          {total > 0 && parts.filter((p) => p.value).map((p) => {
            const len = (p.value / total) * c;
            const el = <circle key={p.label} cx="50" cy="50" r={r} fill="none" stroke={p.color} strokeWidth="12" strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset} />;
            offset += len;
            return el;
          })}
        </svg>
        <div className="absolute inset-0 grid place-items-center text-center">{center ?? <span className="text-xl font-bold">{total}</span>}</div>
      </div>
      <ul className="w-full min-w-0 space-y-1.5 text-sm">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-2 text-muted"><span className="size-2.5 shrink-0 rounded-full" style={{ background: p.color }} />{p.label}</span>
            <span className="font-semibold tabular-nums text-ink">{p.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button icon={done ? Check : Copy} onClick={() => navigator.clipboard.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); })}>
      {done ? "Copied" : "Copy"}
    </Button>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block min-w-0 text-sm">
      <span className="mb-1.5 block text-[13px] font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

/** Company initials in a soft square (no logos are stored). */
export function CompanyAvatar({ name, size = "md" }: { name: string; size?: "md" | "lg" }) {
  const letters = name.replace(/[^\p{L}\p{N} ]/gu, "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
  const hues = ["bg-primary-50 text-primary", "bg-ai-50 text-ai", "bg-info-bg text-info", "bg-offer-bg text-offer", "bg-warn-bg text-warn"];
  const hue = hues[[...name].reduce((s, ch) => s + ch.charCodeAt(0), 0) % hues.length];
  return (
    <span className={`grid shrink-0 place-items-center rounded-control font-semibold ${hue} ${size === "lg" ? "size-14 text-lg" : "size-10 text-sm"}`} aria-hidden>
      {letters}
    </span>
  );
}

/** Wrapper for desktop tables: header on canvas, roomy rows, scroll inside the card only. */
export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-card border border-line bg-surface shadow-card">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line bg-canvas text-xs font-semibold uppercase tracking-wide text-muted">
            <tr>{head.map((h, i) => <th key={i} scope="col" className="whitespace-nowrap px-4 py-3">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-line">{children}</tbody>
        </table>
      </div>
    </div>
  );
}

export const formatDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "–";

export function formatTime(seconds: number) {
  const s = Math.floor(seconds);
  return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, "0")).join(":");
}
