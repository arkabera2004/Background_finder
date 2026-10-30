import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
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

export interface RunView {
  id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  depth: string;
  steps: Record<string, RunStepView>;
  brief: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

export interface Prospect {
  id: string;
  full_name: string;
  linkedin_url: string | null;
  tags: string[];
  status: string;
  source_run_id: string | null;
  created_at: string;
  brief: Record<string, unknown> | null;
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
