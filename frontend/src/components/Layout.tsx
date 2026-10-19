// Page frame. Desktop: collapsible sidebar + top header. Phone/tablet: compact header, slide-in drawer, bottom nav.
import {
  Activity, Bot, Briefcase, Building2, ChevronRight, FileUser, Flag, Globe, LayoutDashboard, LogOut, Menu, PanelLeftClose, PanelLeftOpen, Search, Send, Settings, Users, X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { setToken } from "../api";
import type { Run } from "../types";
import { useFetch } from "../useFetch";

// Every section has its own colour: the menu icon, the page accent (PageTitle bar, background wash) and the phone nav.
// Full class names are written out so Tailwind keeps them.
const TONES = {
  teal: { chip: "bg-teal-100 text-teal-700", on: "bg-teal-500", text: "text-teal-700", hex: "#2dd4bf" },
  amber: { chip: "bg-amber-100 text-amber-700", on: "bg-amber-500", text: "text-amber-700", hex: "#fbbf24" },
  sky: { chip: "bg-sky-100 text-sky-700", on: "bg-sky-500", text: "text-sky-700", hex: "#38bdf8" },
  cyan: { chip: "bg-cyan-100 text-cyan-700", on: "bg-cyan-500", text: "text-cyan-700", hex: "#22d3ee" },
  lime: { chip: "bg-lime-100 text-lime-700", on: "bg-lime-500", text: "text-lime-700", hex: "#a3e635" },
  emerald: { chip: "bg-emerald-100 text-emerald-700", on: "bg-emerald-500", text: "text-emerald-700", hex: "#34d399" },
  rose: { chip: "bg-rose-100 text-rose-700", on: "bg-rose-400", text: "text-rose-600", hex: "#fb7185" },
  pink: { chip: "bg-pink-100 text-pink-700", on: "bg-pink-400", text: "text-pink-600", hex: "#f472b6" },
  orange: { chip: "bg-orange-100 text-orange-700", on: "bg-orange-400", text: "text-orange-600", hex: "#fb923c" },
  yellow: { chip: "bg-yellow-100 text-yellow-700", on: "bg-yellow-500", text: "text-yellow-700", hex: "#facc15" },
  slate: { chip: "bg-slate-100 text-slate-600", on: "bg-slate-500", text: "text-slate-700", hex: "#94a3b8" },
};
// sub = a sub-module of the item above it (Jobs → Job boards, Source health): shown when that group is open.
type Item = { to: string; label: string; icon: LucideIcon; tone: keyof typeof TONES; sub?: boolean; ai?: boolean };
const GROUP = "/jobs";                                      // the expandable menu item
const GROUP_PAGES = ["/jobs", "/job-boards", "/sources"];   // pages that open it automatically
const MENU: Item[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, tone: "teal" },
  { to: "/strategy", label: "Goal & strategy", icon: Flag, tone: "amber" },
  { to: "/jobs", label: "Jobs", icon: Briefcase, tone: "sky" },
  { to: "/job-boards", label: "Job boards", icon: Globe, tone: "cyan", sub: true },
  { to: "/sources", label: "Source health", icon: Activity, tone: "lime", sub: true },
  { to: "/applications", label: "Applications", icon: Send, tone: "emerald" },
  { to: "/cv", label: "My CV", icon: FileUser, tone: "rose" },
  { to: "/recruiters", label: "Recruiters", icon: Users, tone: "pink" },
  { to: "/recruiter-jobs", label: "Recruiter jobs", icon: Building2, tone: "yellow" },
  { to: "/automation", label: "Automation", icon: Bot, tone: "orange", ai: true },
  { to: "/settings", label: "Settings", icon: Settings, tone: "slate" },
];

/** The menu item a page belongs to (/jobs/12 → Jobs). */
function sectionOf(path: string): Item {
  return [...MENU].sort((a, b) => b.to.length - a.to.length).find((m) => (m.to === "/" ? path === "/" : path.startsWith(m.to))) ?? MENU[0];
}
const BOTTOM = ["/", "/jobs", "/applications", "/strategy"];

function readCollapsed() {
  try { return localStorage.getItem("sidebar") === "collapsed"; } catch { return false; }
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <span className="grid size-9 shrink-0 place-items-center rounded-control bg-brand-strong text-white shadow-md shadow-amber-500/20"><Briefcase className="size-[18px]" aria-hidden /></span>
      {!compact && (
        <span className="min-w-0 leading-tight">
          <span className="block truncate text-sm font-bold text-ink">Job Application</span>
          <span className="block truncate text-[11px] text-muted">Find · match · apply</span>
        </span>
      )}
    </span>
  );
}

function initials(name?: string) {
  return (name ?? "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
}

function AutomationPill({ run, compact }: { run: Run | null; compact?: boolean }) {
  const look = run?.status === "RUNNING" ? { text: "Running", dot: "bg-ok-strong animate-pulse-dot", box: "bg-ok-bg text-ok" }
    : run?.status === "PAUSED" ? { text: "Paused", dot: "bg-amber-500", box: "bg-warn-bg text-warn" }
    : { text: "Idle", dot: "bg-slate-400", box: "bg-neutral-bg text-neutral" };
  return (
    <Link to="/automation" title={`Automation: ${look.text}`} aria-label={`Automation: ${look.text}`}
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-80 ${look.box}`}>
      <span className={`size-2 rounded-full ${look.dot}`} />
      {!compact && <span>Automation · {look.text}</span>}
    </Link>
  );
}

export default function Layout() {
  const [drawer, setDrawer] = useState(false);
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  const { data: profile } = useFetch("/api/profile");
  const { data: run } = useFetch<Run | null>("/api/automation/status", 10);

  useEffect(() => setDrawer(false), [location.pathname]);
  // Jobs group: open on any Jobs page; otherwise as you left it.
  const [groupOpen, setGroupOpen] = useState(() => {
    try { return localStorage.getItem("jobs-menu") === "open"; } catch { return false; }
  });
  const toggleGroup = (open: boolean) => {
    setGroupOpen(open);
    try { localStorage.setItem("jobs-menu", open ? "open" : "closed"); } catch { /* private mode */ }
  };
  useEffect(() => {
    if (GROUP_PAGES.some((p) => location.pathname.startsWith(p))) setGroupOpen(true);
  }, [location.pathname]);
  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [drawer]);

  function toggleCollapsed() {
    setCollapsed((c) => {
      try { localStorage.setItem("sidebar", c ? "open" : "collapsed"); } catch { /* private mode */ }
      return !c;
    });
  }

  function search(e: FormEvent) {
    e.preventDefault();
    navigate(`/jobs?q=${encodeURIComponent(query.trim())}`);
    setSearchOpen(false);
  }

  function logout() {
    setToken(null);
    window.location.href = "/";
  }

  const section = sectionOf(location.pathname);

  const nav = (rail: boolean) => (
    <nav className="space-y-1" aria-label="Main">
      {MENU.filter((m) => !m.sub || groupOpen).map(({ to, label, icon: Icon, sub, ai, tone }) => (
        <div key={to} className={`flex items-center gap-1 ${sub ? "animate-fade-in" : ""}`}>
        <NavLink to={to} end={to === "/"} title={rail ? label : undefined} onClick={to === GROUP ? () => toggleGroup(true) : undefined}
          className={({ isActive }) =>
            `group flex min-w-0 flex-1 items-center gap-3 rounded-control px-2 py-1.5 text-sm font-medium transition-colors duration-150 ${
              rail ? "justify-center px-0" : sub ? "ml-4 text-[13px]" : ""} ${
              isActive ? "bg-white text-ink shadow-sm ring-1 ring-black/5" : "text-slate-600 hover:bg-white/70 hover:text-ink"}`}>
          {({ isActive }) => (
            <>
              <span className={`grid shrink-0 place-items-center rounded-[8px] transition-colors ${sub ? "size-7" : "size-8"} ${
                isActive ? `${TONES[tone].on} text-white shadow-md` : TONES[tone].chip}`}>
                <Icon className={sub ? "size-3.5" : "size-4"} aria-hidden />
              </span>
              {!rail && <span className="truncate">{label}</span>}
              {!rail && ai && <span className="ml-auto rounded-full bg-ai-100 px-1.5 py-0.5 text-[10px] font-semibold text-ai">AI</span>}
            </>
          )}
        </NavLink>
        {to === GROUP && !rail && (
          <button type="button" onClick={() => toggleGroup(!groupOpen)} aria-expanded={groupOpen}
            aria-label={groupOpen ? "Hide Job boards and Source health" : "Show Job boards and Source health"}
            className="grid size-8 shrink-0 place-items-center rounded-control text-slate-500 transition-colors hover:bg-white/70 hover:text-ink">
            <ChevronRight className={`size-4 transition-transform duration-200 ${groupOpen ? "rotate-90" : ""}`} aria-hidden />
          </button>
        )}
        </div>
      ))}
    </nav>
  );

  const userBlock = (rail: boolean) => (
    <div className={`border-t border-black/5 pt-3 ${rail ? "space-y-2" : ""}`}>
      <div className={`flex items-center gap-3 rounded-control px-2 py-2 ${rail ? "justify-center px-0" : ""}`}>
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-brand text-sm font-semibold text-teal-800 ring-2 ring-white" aria-hidden>{initials(profile?.name)}</span>
        {!rail && (
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-ink">{profile?.name ?? "…"}</span>
            <span className="block truncate text-xs text-muted">{profile?.headline ?? ""}</span>
          </span>
        )}
      </div>
      <button onClick={logout} title="Log out" aria-label="Log out"
        className={`flex w-full items-center gap-3 rounded-control px-3 py-2 text-sm text-slate-500 transition-colors hover:bg-white/70 hover:text-ink ${rail ? "justify-center px-0" : ""}`}>
        <LogOut className="size-[18px]" aria-hidden />{!rail && "Log out"}
      </button>
    </div>
  );

  const sidebarWidth = collapsed ? "lg:pl-[72px]" : "lg:pl-[248px]";

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-black/5 bg-sidebar p-3 transition-[width] duration-200 lg:flex ${collapsed ? "w-[72px]" : "w-[248px]"}`}>
        <div className={`mb-5 flex items-center px-1 pt-1 ${collapsed ? "justify-center" : "justify-between"}`}>
          <Link to="/" aria-label="Dashboard"><Logo compact={collapsed} /></Link>
        </div>
        <div className="flex-1 overflow-y-auto">{nav(collapsed)}</div>
        <button onClick={toggleCollapsed} title={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`mb-2 flex items-center gap-3 rounded-control px-3 py-2 text-sm text-slate-500 hover:bg-white/70 hover:text-ink ${collapsed ? "justify-center px-0" : ""}`}>
          {collapsed ? <PanelLeftOpen className="size-[18px]" /> : <><PanelLeftClose className="size-[18px]" /> Collapse</>}
        </button>
        {userBlock(collapsed)}
      </aside>

      {/* Phone / tablet drawer */}
      <div className={`fixed inset-0 z-40 lg:hidden ${drawer ? "" : "pointer-events-none"}`} inert={!drawer}>
        <div className={`absolute inset-0 bg-slate-900/40 transition-opacity duration-200 ${drawer ? "opacity-100" : "opacity-0"}`} onClick={() => setDrawer(false)} />
        <aside role="dialog" aria-modal="true" aria-label="Menu"
          className={`absolute inset-y-0 left-0 flex w-[280px] max-w-[85vw] flex-col bg-sidebar p-3 shadow-lift transition-transform duration-200 ${drawer ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="mb-5 flex items-center justify-between px-1 pt-1">
            <Logo />
            <button onClick={() => setDrawer(false)} className="rounded-control p-2 text-muted hover:bg-white/70" aria-label="Close menu"><X className="size-5" /></button>
          </div>
          <div className="flex-1 overflow-y-auto">{nav(false)}</div>
          {userBlock(false)}
        </aside>
      </div>

      <div className={`transition-[padding] duration-200 ${sidebarWidth}`}>
        {/* Top header */}
        <header className="sticky top-0 z-20 bg-surface/80 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button onClick={() => setDrawer(true)} className="-ml-1 rounded-control p-2 text-slate-600 hover:bg-canvas lg:hidden" aria-label="Open menu">
              <Menu className="size-5" />
            </button>
            <Link to="/" className={`lg:hidden ${searchOpen ? "hidden sm:block" : ""}`} aria-label="Dashboard"><Logo compact /></Link>

            <form onSubmit={search} role="search" className={`${searchOpen ? "flex" : "hidden"} min-w-0 flex-1 sm:flex sm:max-w-md`}>
              <label className="relative w-full">
                <span className="sr-only">Search jobs</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search jobs, companies, cities…"
                  className="w-full rounded-control border border-line bg-canvas py-2 pl-9 pr-3 text-sm transition-colors focus:border-primary focus:bg-surface focus:outline-none focus:ring-4 focus:ring-primary/15" />
              </label>
            </form>

            <div className="ml-auto flex items-center gap-2">
              <button onClick={() => setSearchOpen(!searchOpen)} className="rounded-control p-2 text-slate-600 hover:bg-canvas sm:hidden" aria-label={searchOpen ? "Close search" : "Search"}>
                {searchOpen ? <X className="size-5" /> : <Search className="size-5" />}
              </button>
              <span className="hidden md:inline-flex"><AutomationPill run={run} /></span>
              <span className={`md:hidden ${searchOpen ? "hidden" : ""}`}><AutomationPill run={run} compact /></span>
              <Link to="/settings" title="Profile & settings" aria-label="Profile and settings"
                className={`grid size-9 place-items-center rounded-full bg-brand text-sm font-semibold text-teal-800 ring-1 ring-black/5 hover:ring-4 hover:ring-teal-500/15 ${searchOpen ? "hidden sm:grid" : ""}`}>
                {initials(profile?.name)}
              </Link>
            </div>
          </div>
          <div className="h-[3px] bg-brand-strong opacity-60" aria-hidden />
        </header>

        <div className="relative" style={{ "--section": TONES[section.tone].hex } as CSSProperties}>
          {/* soft wash in the section's colour behind the page title */}
          <div className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-[0.22]" aria-hidden
            style={{ background: "radial-gradient(700px 240px at 15% 0%, var(--section), transparent 70%)" }} />
          <main key={location.pathname} className="relative mx-auto max-w-7xl animate-fade-in px-4 pb-24 pt-5 sm:px-6 sm:pt-7 lg:px-8 lg:pb-10">
            <Outlet />
          </main>
        </div>
      </div>

      {/* Phone bottom nav */}
      <nav aria-label="Quick" className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
        {MENU.filter((m) => BOTTOM.includes(m.to)).map(({ to, label, icon: Icon, tone }) => (
          <NavLink key={to} to={to} end={to === "/"}
            className={({ isActive }) => `flex flex-col items-center gap-1 py-2 text-[11px] font-medium transition-colors ${isActive ? TONES[tone].text : "text-muted hover:text-ink"}`}>
            {({ isActive }) => (
              <>
                <span className={`grid h-7 w-12 place-items-center rounded-full transition-colors ${isActive ? `${TONES[tone].on} text-white shadow-md` : ""}`}><Icon className="size-[18px]" aria-hidden /></span>
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
