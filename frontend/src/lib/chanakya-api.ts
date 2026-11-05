/**
 * Chanakya API client: kept separate from lib/api.ts (ProspectLens's
 * single-prospect client) since Chanakya is an additive monthly batch
 * product with its own run lifecycle, not an extension of the
 * single-prospect types/endpoints.
 */
import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ChanakyaApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) throw new ChanakyaApiError(res.status, await res.text());
  return res.json();
}

export type AgentName =
  | "catalogue"
  | "company_scout"
  | "people_finder"
  | "linkedin_resolver"
  | "email_hunter"
  | "profile_researcher"
  | "qa_sync";

export interface AgentExecutionView {
  agent_name: AgentName;
  status: "pending" | "running" | "completed" | "failed" | "retrying";
  retry_count: number;
  error: string | null;
  output_summary: Record<string, unknown>;
}

export interface MonthlyRun {
  id: string;
  period: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  config: Record<string, unknown>;
  created_at: string;
  completed_at: string | null;
  agent_executions: AgentExecutionView[];
}

export interface OfferingInput {
  name: string;
  description?: string;
  icp_criteria?: string[];
}

export interface OfferingSnapshot {
  id: string;
  run_id: string;
  version: number;
  data: { offerings: OfferingInput[]; filters: Record<string, unknown> };
  created_at: string;
}

export interface ScoutedCompanyView {
  id: string;
  run_id: string;
  name: string;
  domain: string;
  fit_score: number;
  selected: boolean;
  source_url: string;
  created_at: string;
}

export interface PersonView {
  id: string;
  run_id: string;
  company_id: string;
  full_name: string;
  role: string;
  linkedin_url: string | null;
  confidence: number;
  identity_confirmed: boolean;
  resolution_status: "pending" | "confirmed" | "ambiguous" | "unresolved";
  candidate_profiles: { linkedin_url: string; title: string | null; snippet: string | null }[];
  created_at: string;
}

export interface EmailCandidateView {
  id: string;
  run_id: string;
  person_id: string;
  email: string;
  pattern: string;
  verification_status: "valid" | "rejected" | "needs_review";
  confidence: number;
  created_at: string;
}

export interface QARecordView {
  id: string;
  run_id: string;
  person_id: string;
  confidence_score: number;
  confidence_level: "high" | "medium" | "low";
  needs_review: boolean;
  draft_subject: string;
  draft_body: string;
  approval_status: "pending_review" | "approved" | "rejected";
  created_at: string;
}

export interface OrchestrateStageResult {
  agent: AgentName;
  status: "completed" | "skipped_already_completed" | "stopped";
  result?: Record<string, unknown>;
  error?: string;
}

export interface OrchestrateResult {
  run_id: string;
  stages: OrchestrateStageResult[];
  stopped_at: AgentName | null;
}

export const chanakyaApi = {
  listRuns: () => request<MonthlyRun[]>("/chanakya/runs"),
  getRun: (runId: string) => request<MonthlyRun>(`/chanakya/runs/${runId}`),
  createRun: (period: string, config?: Record<string, unknown>) =>
    request<MonthlyRun>("/chanakya/runs", {
      method: "POST",
      body: JSON.stringify({ period, config: config ?? {} }),
    }),
  submitOfferings: (runId: string, offerings: OfferingInput[], filters: Record<string, unknown> = {}) =>
    request<OfferingSnapshot>(`/chanakya/runs/${runId}/offerings`, {
      method: "POST",
      body: JSON.stringify({ offerings, filters }),
    }),
  listOfferings: (runId: string) => request<OfferingSnapshot[]>(`/chanakya/runs/${runId}/offerings`),
  orchestrate: (runId: string) =>
    request<OrchestrateResult>(`/chanakya/runs/${runId}/orchestrate`, { method: "POST" }),
  listCompanies: (runId: string, selectedOnly = false) =>
    request<ScoutedCompanyView[]>(`/chanakya/runs/${runId}/companies?selected_only=${selectedOnly}`),
  listPeople: (runId: string) => request<PersonView[]>(`/chanakya/runs/${runId}/people`),
  listPeopleNeedingReview: (runId: string) =>
    request<PersonView[]>(`/chanakya/runs/${runId}/people/needs-review`),
  resolvePersonManually: (runId: string, personId: string, linkedinUrl: string) =>
    request<PersonView>(`/chanakya/runs/${runId}/people/${personId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ linkedin_url: linkedinUrl }),
    }),
  listEmails: (runId: string) => request<EmailCandidateView[]>(`/chanakya/runs/${runId}/emails`),
  listQaRecords: (runId: string, needsReviewOnly = false) =>
    request<QARecordView[]>(`/chanakya/runs/${runId}/qa?needs_review_only=${needsReviewOnly}`),
  approveQaRecord: (runId: string, personId: string, approve: boolean) =>
    request<QARecordView>(`/chanakya/runs/${runId}/qa/${personId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approve }),
    }),
  exportBlobUrl: async (runId: string, format: "json" | "csv") => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    const res = await fetch(`${API_URL}/chanakya/runs/${runId}/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ChanakyaApiError(res.status, await res.text());
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
};
