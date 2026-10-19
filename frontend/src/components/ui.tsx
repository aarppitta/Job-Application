// Building blocks used by every page. Colors come from the tokens in index.css and the status config in theme.ts.
import { CircleAlert, Copy, Check, Inbox, LoaderCircle, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { APP_STATUS, MATCH_LEVEL, VISA, scoreTone, type Look } from "../theme";

export const inputClass =
  "w-full rounded-control border border-input bg-surface px-3 py-2 text-sm text-ink placeholder:text-slate-400 " +
  "transition-[border-color,box-shadow] duration-150 focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/15 " +
  "disabled:cursor-not-allowed disabled:bg-canvas disabled:text-muted";

// Card icon colours: picked from the title, so the same card always has the same colour and a page gets variety.
const CARD_TONES = ["bg-teal-100 text-teal-700", "bg-sky-100 text-sky-700", "bg-emerald-100 text-emerald-600", "bg-amber-100 text-amber-600",
  "bg-pink-100 text-pink-600", "bg-lime-100 text-lime-700", "bg-orange-100 text-orange-600", "bg-cyan-100 text-cyan-700"];
const toneFor = (key: string) => CARD_TONES[[...key].reduce((s, ch) => s + ch.charCodeAt(0), 0) % CARD_TONES.length];

export function Card({ title, subtitle, icon: Icon, right, children, ai, className = "" }: {
  title?: ReactNode; subtitle?: ReactNode; icon?: LucideIcon; right?: ReactNode; children: ReactNode; ai?: boolean; className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-card border p-4 shadow-card sm:p-5 ${ai ? "border-ai-100 bg-gradient-to-br from-ai-50/80 via-surface to-surface" : "border-line/80 bg-surface"} ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {Icon && (
              <span className={`grid size-9 shrink-0 place-items-center rounded-control ${ai ? "bg-ai-100 text-ai" : toneFor(typeof title === "string" ? title : "card")}`}>
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
  primary: "bg-grad-primary text-white shadow-sm shadow-teal-500/20 hover:brightness-105 hover:shadow-md hover:shadow-teal-500/25",
  normal: "border border-line bg-surface text-ink hover:bg-primary-50 hover:border-primary/30 hover:text-primary",
  danger: "border border-red-200 bg-surface text-bad hover:bg-bad-bg",
  success: "bg-grad-success text-white shadow-sm shadow-emerald-500/20 hover:brightness-105",
  ai: "bg-grad-ai text-white shadow-sm shadow-orange-500/20 hover:brightness-105",
  ghost: "text-muted hover:bg-canvas hover:text-ink",
};
export const buttonClass = (kind: ButtonKind = "normal") =>
  "inline-flex items-center justify-center gap-2 rounded-control px-3.5 py-2 text-sm font-medium transition-all duration-150 " +
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
        {/* accent in the colour of the current menu section (set by Layout as --section) */}
        <span className="mb-2 block h-1.5 w-12 rounded-full" style={{ background: "linear-gradient(90deg, var(--section, #2dd4bf), #fde68a)" }} aria-hidden />
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
        on ? "border-teal-300 bg-teal-50 text-teal-800" : "border-line bg-surface text-muted hover:border-primary/30 hover:bg-primary-50 hover:text-primary"}`}>
      {children}
      {count !== undefined && <span className={`rounded-full px-1.5 tabular-nums ${on ? "bg-teal-200/70 text-teal-900" : "bg-canvas"}`}>{count}</span>}
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
      <span className="mb-3 grid size-12 place-items-center rounded-full bg-brand text-teal-700 ring-1 ring-black/5"><Icon className="size-6" aria-hidden /></span>
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
  // tinted tile + solid icon + coloured number, one colour family per tone
  const look = {
    primary: { box: "from-sky-50 border-sky-100", icon: "bg-sky-100 text-sky-700", num: "text-sky-700" },
    ok: { box: "from-emerald-50 border-emerald-100", icon: "bg-emerald-100 text-emerald-700", num: "text-emerald-700" },
    bad: { box: "from-rose-50 border-rose-100", icon: "bg-rose-100 text-rose-600", num: "text-rose-600" },
    violet: { box: "from-pink-50 border-pink-100", icon: "bg-pink-100 text-pink-600", num: "text-pink-600" },
    offer: { box: "from-teal-50 border-teal-100", icon: "bg-teal-100 text-teal-700", num: "text-teal-700" },
    warn: { box: "from-amber-50 border-amber-100", icon: "bg-amber-100 text-amber-700", num: "text-amber-700" },
    ai: { box: "from-orange-50 border-orange-100", icon: "bg-orange-100 text-orange-600", num: "text-orange-600" },
  }[tone];
  return (
    <div className={`min-w-0 rounded-card border bg-gradient-to-br to-surface p-4 shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-lift ${look.box}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[13px] font-medium leading-snug text-slate-600">{label}</p>
        <span className={`grid size-9 shrink-0 place-items-center rounded-control ${look.icon}`}><Icon className="size-4" aria-hidden /></span>
      </div>
      <p className={`mt-2 text-2xl font-bold tabular-nums sm:text-[28px] ${look.num}`}>{value ?? "–"}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function ProgressBar({ value, tone = "primary", label }: { value: number; tone?: "primary" | "ok" | "ai"; label?: string }) {
  const bar = { primary: "bg-grad-primary", ok: "bg-grad-success", ai: "bg-grad-ai" }[tone];
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
          <thead className="border-b border-teal-100 bg-gradient-to-r from-teal-50 via-amber-50/70 to-rose-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
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
