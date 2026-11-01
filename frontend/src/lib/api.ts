import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export type NetworkErrorKind = "timeout" | "network";

export class NetworkError extends Error {
  constructor(public kind: NetworkErrorKind, message: string) {
    super(message);
  }
}

const REQUEST_TIMEOUT_MS = 20_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new NetworkError("timeout", "The request timed out. Please try again.");
    }
    // A plain fetch rejection here (not an ApiError) means the request never reached
    // the server as an HTTP response — most commonly a CORS block or the backend
    // being unreachable, not a backend-side error.
    throw new NetworkError(
      "network",
      "Could not reach the server. Check your connection and that the backend is running."
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json();
}

export interface Me {
  id: string;
  email: string | null;
}

export type ResearchDepth = "quick" | "standard" | "deep";

export interface ResearchRequest {
  linkedin_url?: string;
  full_name?: string;
  company?: string;
  pasted_text?: string;
  depth?: ResearchDepth;
}

export interface RunStepView {
  status: "pending" | "running" | "completed" | "failed";
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export type Confidence = "high" | "medium" | "low";

export type SourceType =
  | "company_website"
  | "company_news"
  | "news_article"
  | "social_profile"
  | "social_post"
  | "other";

export interface BriefSource {
  id: string;
  url: string;
  title: string | null;
  excerpt: string | null;
  publisher: string | null;
  source_type: SourceType;
  published_at: string | null;
  retrieved_at: string | null;
  confidence: Confidence;
}

export interface BriefClaim {
  text: string;
  source_ids: string[];
  confidence: Confidence;
  is_inference: boolean;
  date: string | null;
}

export interface CareerEntry {
  organization: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  source_ids: string[];
  confidence: Confidence;
}

export type ActivityType =
  | "original_post"
  | "repost_or_share"
  | "comment"
  | "article_or_publication"
  | "interview_or_podcast"
  | "talk_or_presentation"
  | "professional_announcement"
  | "other_public_activity";

export interface ActivityItem {
  activity_type: ActivityType;
  topic: string;
  summary: string;
  url: string;
  published_at: string | null;
  authored_by_person: boolean;
  relevance: string | null;
  confidence: Confidence;
  source_ids: string[];
}

export interface PersonalizationHook {
  evidence: string;
  relevance: string;
  outreach_angle: string;
  source_ids: string[];
  confidence: Confidence;
}

export interface OutreachStrategy {
  angle: string | null;
  primary_hooks: string[];
  question_or_value_prop: string | null;
  opening_approach: string | null;
  avoid: string[];
}

export interface ResearchGaps {
  missing_information: string[];
  limited_coverage_areas: string[];
  conflicting_information: string[];
  unverified_claims: string[];
  inaccessible_sources: string[];
}

export interface SynthesisMetadata {
  synthesis_method: "ai" | "rule_based";
  provider: string | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
}

export interface ProspectBrief {
  prospect_name: string;
  snapshot: BriefClaim[];
  current_role: BriefClaim[];
  company_overview: BriefClaim[];
  career_timeline: CareerEntry[];
  expertise: BriefClaim[];
  activity: ActivityItem[];
  recurring_themes: BriefClaim[];
  company_context: BriefClaim[];
  communication_style: BriefClaim[];
  likely_priorities: BriefClaim[];
  personalization_hooks: PersonalizationHook[];
  outreach_strategy: OutreachStrategy;
  sources: BriefSource[];
  research_gaps: ResearchGaps;
  _synthesis_metadata?: SynthesisMetadata;
}

export interface IdentityCandidate {
  linkedin_url: string;
  title: string | null;
  snippet: string | null;
}

export interface RunView {
  id: string;
  status: "pending" | "running" | "needs_identity_selection" | "completed" | "failed" | "cancelled";
  depth: string;
  steps: Record<string, RunStepView>;
  brief: ProspectBrief | null;
  created_at: string;
  completed_at: string | null;
  identity_candidates: IdentityCandidate[];
}

export interface Prospect {
  id: string;
  full_name: string;
  linkedin_url: string | null;
  tags: string[];
  status: string;
  source_run_id: string | null;
  created_at: string;
  brief: ProspectBrief | null;
}

export interface Company {
  id: string;
  name: string;
  domain: string | null;
  data: Record<string, unknown>;
  crawled_at: string | null;
  created_at: string;
}

export type ExportFormat = "json" | "md" | "pdf";

export const api = {
  health: () => request<{ status: string }>("/health"),
  me: () => request<Me>("/me"),
  createResearch: (body: ResearchRequest) =>
    request<{ run_id: string; status: string }>("/research", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getRun: (runId: string) => request<RunView>(`/runs/${runId}`),
  selectIdentity: (runId: string, linkedinUrl: string) =>
    request<{ run_id: string; status: string }>(
      `/runs/${runId}/select-identity?linkedin_url=${encodeURIComponent(linkedinUrl)}`,
      { method: "POST" }
    ),
  cancelRun: (runId: string) =>
    request<{ run_id: string; status: string }>(`/runs/${runId}/cancel`, { method: "POST" }),
  retryRun: (runId: string) =>
    request<{ run_id: string; status: string }>(`/runs/${runId}/retry`, { method: "POST" }),
  saveProspect: (runId: string) =>
    request<Prospect>("/prospects", { method: "POST", body: JSON.stringify({ run_id: runId }) }),
  listProspects: () => request<Prospect[]>("/prospects"),
  getProspect: (id: string) => request<Prospect>(`/prospects/${id}`),
  deleteProspect: async (id: string) => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    const res = await fetch(`${API_URL}/prospects/${id}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
  },
  exportBriefUrl: async (id: string, format: ExportFormat) => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    const res = await fetch(`${API_URL}/prospects/${id}/brief/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
  listCompanies: () => request<Company[]>("/companies"),
  getCompany: (id: string) => request<Company>(`/companies/${id}`),
  deleteCompany: async (id: string) => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    const res = await fetch(`${API_URL}/companies/${id}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
  },
};
