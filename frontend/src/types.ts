// Shapes of the data returned by the backend.

export type Job = {
  id: number;
  title: string;
  company: string;
  location: string | null;
  country: string | null;
  remote_type: string;
  employment_type: string | null;
  source: string;
  source_url: string | null;
  application_url: string | null;
  company_url: string | null;
  posted_at: string | null;
  discovered_at: string;
  visa_status: "confirmed" | "unclear" | "unlikely";
  language_requirement: string;
  experience_required: number | null;
  seniority: string | null;
  risk_flags: string[];
  description_incomplete: boolean;
  ats_score: number | null;
  status: string;
  is_saved: boolean;
  top_skills: string[];
  application_status: string | null;
  match: { level: "good" | "stretch" | "low" | "unknown"; text: string };
  updated_at: string | null;
};

export type Score = {
  overall: number;
  parts: Record<string, number>;
  matched_skills: string[];
  missing_skills: string[];
  reasons: string[];
  concerns: string[];
  recommendation: "APPLY" | "REVIEW" | "SKIP" | "RISK";
  threshold: number;
  created_at: string;
};

export type JobDetails = Job & {
  description: string;
  parsed: { requirements: string[]; salary: { min?: number; max?: number }; visa_evidence: string[] };
  score: Score | null;
  sources: { source: string; url: string | null; first_seen: string }[];
  versions: number;
  application_id: number | null;
};

export type Application = {
  id: number;
  job_id: number;
  status: string;
  submitted_at: string;
  score: number | null;
  jd_version: number | null;
  cover_letter: string | null;
  notes: string | null;
  history: { status: string; at: string }[];
  job: { id: number; title: string; company: string; location: string | null; application_url: string | null };
};

export type Run = {
  id: number;
  status: "RUNNING" | "PAUSED" | "STOPPED" | "FINISHED" | "FAILED";
  started_at: string;
  runtime_seconds: number;
  config: { max_runtime_hours: number; min_score: number };
  discovered: number;
  duplicates: number;
  qualified: number;
  errors: number;
  summary: string | null;
};
