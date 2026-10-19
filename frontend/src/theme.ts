// One place for every status color + icon. Every page uses these, so "Applied" looks the same everywhere.
import {
  Award, BadgeCheck, CalendarClock, Circle, CircleCheck, CircleDot, CircleMinus, CircleX, Hourglass, Lightbulb,
  MessageSquareQuote, MessageSquareReply, SearchX, ShieldCheck, ShieldQuestion, ShieldX, type LucideIcon,
} from "lucide-react";

export type Look = { label: string; className: string; icon?: LucideIcon };

/** Application status (the pipeline after you applied). Same look everywhere. */
export const APP_STATUS: Record<string, Look> = {
  APPLIED: { label: "Applied", className: "bg-ok-bg text-ok", icon: CircleCheck },
  RECRUITER_CONTACTED: { label: "Recruiter contacted", className: "bg-pending-bg text-pending", icon: Hourglass },
  RECRUITER_REPLIED: { label: "Recruiter replied", className: "bg-info-bg text-info", icon: MessageSquareReply },
  HR_SCREEN: { label: "HR screen", className: "bg-violet-bg text-violet", icon: CalendarClock },
  TECHNICAL: { label: "Technical interview", className: "bg-violet-bg text-violet", icon: CalendarClock },
  TAKE_HOME: { label: "Take-home", className: "bg-violet-bg text-violet", icon: CalendarClock },
  HIRING_MANAGER: { label: "Hiring manager", className: "bg-violet-bg text-violet", icon: CalendarClock },
  FINAL: { label: "Final interview", className: "bg-violet-bg text-violet", icon: CalendarClock },
  OFFER: { label: "Offer", className: "bg-offer text-white", icon: Award },
  REJECTED: { label: "Rejected", className: "bg-bad-bg text-bad", icon: CircleX },
  WITHDRAWN: { label: "Withdrawn", className: "bg-neutral-bg text-neutral", icon: CircleMinus },
};
export const APP_STATUSES = Object.keys(APP_STATUS);
export const INTERVIEW_STAGES = ["HR_SCREEN", "TECHNICAL", "TAKE_HOME", "HIRING_MANAGER", "FINAL"];

/** Where a rejection happened: drives "learning from rejections" on the Strategy page. */
export const REJECTION_STAGES: Record<string, string> = {
  CV_SCREENING: "CV screening", HR: "HR call", TECHNICAL: "Technical interview", TAKE_HOME: "Take-home",
  HIRING_MANAGER: "Hiring manager", FINAL: "Final round", UNKNOWN: "Unknown",
};

/** Your CV vs one requirement: 🟢 strong · 🟡 partial · 🔴 missing · ⚪ not relevant. */
export const REQ_STATUS: Record<string, Look> = {
  strong: { label: "Strong match", className: "bg-ok-bg text-ok", icon: CircleCheck },
  partial: { label: "Partial", className: "bg-warn-bg text-warn", icon: CircleDot },
  missing: { label: "Missing", className: "bg-bad-bg text-bad", icon: CircleX },
  not_relevant: { label: "Show in interview", className: "bg-neutral-bg text-neutral", icon: Circle },
};

/** Research claims: where a fact comes from. */
export const FACT_STATUS: Record<string, Look> = {
  confirmed: { label: "Confirmed", className: "bg-ok-bg text-ok", icon: BadgeCheck },
  reported: { label: "Reported", className: "bg-info-bg text-info", icon: MessageSquareQuote },
  estimated: { label: "Estimated", className: "bg-warn-bg text-warn", icon: Lightbulb },
  not_found: { label: "Not found", className: "bg-neutral-bg text-neutral", icon: SearchX },
  could_not_verify: { label: "Could not verify", className: "bg-neutral-bg text-neutral", icon: ShieldQuestion },
};

/** Probability / level words → colors (Very High … Low). */
export const LEVEL_LOOK: Record<string, string> = {
  "Very High": "bg-ok-bg text-ok", High: "bg-info-bg text-info", Medium: "bg-warn-bg text-warn", Low: "bg-bad-bg text-bad",
};

/** Final decision for a job. */
export const DECISION: Record<string, { className: string; ring: string }> = {
  APPLY: { className: "bg-ok-strong text-white", ring: "border-green-200 bg-ok-bg/50" },
  LEARN: { className: "bg-amber-500 text-white", ring: "border-amber-200 bg-warn-bg/50" },
  SKIP: { className: "bg-slate-500 text-white", ring: "border-line bg-canvas" },
};

/** Match verdict of a job (from the backend's match_label). */
export const MATCH_LEVEL: Record<string, Look> = {
  good: { label: "Good match", className: "bg-ok-bg text-ok", icon: CircleCheck },
  stretch: { label: "Stretch", className: "bg-warn-bg text-warn" },
  low: { label: "Not a match", className: "bg-neutral-bg text-neutral" },
  unknown: { label: "Not scored", className: "bg-neutral-bg text-neutral" },
};

/** Visa sponsorship found in the job description. */
export const VISA: Record<string, Look> = {
  confirmed: { label: "Sponsorship confirmed", className: "bg-ok-bg text-ok", icon: ShieldCheck },
  unclear: { label: "Sponsorship unclear", className: "bg-neutral-bg text-neutral", icon: ShieldQuestion },
  unlikely: { label: "Sponsorship unlikely", className: "bg-bad-bg text-bad", icon: ShieldX },
};

/** Score colors: 90+ green, 75–89 blue, 60–74 amber, below 60 grey. */
export function scoreTone(score: number) {
  if (score >= 90) return { label: "Excellent match", text: "text-ok", bg: "bg-ok-bg", stroke: "var(--color-ok-strong)" };
  if (score >= 75) return { label: "Strong match", text: "text-primary", bg: "bg-primary-50", stroke: "var(--color-primary)" };
  if (score >= 60) return { label: "Partial match", text: "text-warn", bg: "bg-warn-bg", stroke: "#f59e0b" };
  return { label: "Weak match", text: "text-neutral", bg: "bg-neutral-bg", stroke: "#94a3b8" };
}
