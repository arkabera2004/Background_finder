"use client";

import {
  BookOpen,
  Gauge,
  Link2,
  Mail,
  ShieldCheck,
  UserSearch,
  Users,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  chanakyaApi,
  type EmailCandidateView,
  type MonthlyRun,
  type OfferingInput,
  type OfferingSnapshot,
  type PersonView,
  type QARecordView,
  type ScoutedCompanyView,
} from "@/lib/chanakya-api";

const STAGE_LABELS: Record<string, string> = {
  catalogue: "Catalogue",
  company_scout: "Company Scout",
  people_finder: "People Finder",
  linkedin_resolver: "LinkedIn Resolver",
  email_hunter: "Email Hunter",
  profile_researcher: "Profile Researcher",
  qa_sync: "QA & Sync",
};

const STAGE_ICONS: Record<string, typeof Gauge> = {
  catalogue: BookOpen,
  company_scout: Gauge,
  people_finder: Users,
  linkedin_resolver: Link2,
  email_hunter: Mail,
  profile_researcher: UserSearch,
  qa_sync: ShieldCheck,
};

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "completed") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

// Each agent's output_summary has a different shape (see the respective
// FastAPI router's complete_agent() call) — this is a display-only best
// effort to surface its one or two most meaningful numbers, not a
// generic key dumper. Real persisted data only, never fabricated.
function stageMetric(agentName: string, summary: Record<string, unknown>): string | null {
  const n = (key: string) => (typeof summary[key] === "number" ? (summary[key] as number) : null);
  switch (agentName) {
    case "catalogue":
      return n("offering_count") !== null ? `${n("offering_count")} offerings` : null;
    case "company_scout":
      return n("selected") !== null ? `${n("selected")} of ${n("candidates_found") ?? "?"} selected` : null;
    case "people_finder":
      return n("people_found") !== null ? `${n("people_found")} people found` : null;
    case "linkedin_resolver":
      return n("confirmed") !== null ? `${n("confirmed")} confirmed, ${n("ambiguous") ?? 0} ambiguous` : null;
    case "email_hunter":
      return n("emails_found") !== null ? `${n("emails_found")} candidates` : null;
    case "profile_researcher":
      return n("completed") !== null ? `${n("completed")} briefs completed` : null;
    case "qa_sync":
      return n("people_processed") !== null ? `${n("people_processed")} scored` : null;
    default:
      return null;
  }
}

export default function ChanakyaRunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [run, setRun] = useState<MonthlyRun | null>(null);
  const [companies, setCompanies] = useState<ScoutedCompanyView[]>([]);
  const [people, setPeople] = useState<PersonView[]>([]);
  const [emails, setEmails] = useState<EmailCandidateView[]>([]);
  const [qaRecords, setQaRecords] = useState<QARecordView[]>([]);
  const [needsReview, setNeedsReview] = useState<PersonView[]>([]);
  const [offeringSnapshots, setOfferingSnapshots] = useState<OfferingSnapshot[]>([]);
  const [resolveUrls, setResolveUrls] = useState<Record<string, string>>({});
  const [offerings, setOfferings] = useState<OfferingInput[]>([]);
  const [offeringName, setOfferingName] = useState("");
  const [icpCriteria, setIcpCriteria] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadAll = async () => {
    try {
      const r = await chanakyaApi.getRun(runId);
      setRun(r);
      const [c, p, e, q, nr, offs] = await Promise.all([
        chanakyaApi.listCompanies(runId).catch(() => []),
        chanakyaApi.listPeople(runId).catch(() => []),
        chanakyaApi.listEmails(runId).catch(() => []),
        chanakyaApi.listQaRecords(runId).catch(() => []),
        chanakyaApi.listPeopleNeedingReview(runId).catch(() => []),
        chanakyaApi.listOfferings(runId).catch(() => []),
      ]);
      setCompanies(c);
      setPeople(p);
      setEmails(e);
      setQaRecords(q);
      setNeedsReview(nr);
      setOfferingSnapshots(offs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load, not a cascading update
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const handleAddOfferingRow = () => {
    if (!offeringName.trim()) return;
    setOfferings((prev) => [
      ...prev.filter((o) => o.name.trim()),
      {
        name: offeringName,
        icp_criteria: icpCriteria
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      },
    ]);
    setOfferingName("");
    setIcpCriteria("");
  };

  const handleRemoveOfferingRow = (index: number) => {
    setOfferings((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmitOffering = async () => {
    const toSubmit = offerings.filter((o) => o.name.trim());
    if (toSubmit.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      await chanakyaApi.submitOfferings(runId, toSubmit);
      setOfferings([]);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit offering brief");
    } finally {
      setBusy(false);
    }
  };

  const handleResolveManually = async (personId: string) => {
    const url = resolveUrls[personId];
    if (!url) return;
    setError(null);
    try {
      await chanakyaApi.resolvePersonManually(runId, personId, url);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve identity");
    }
  };

  const handleOrchestrate = async () => {
    setBusy(true);
    setError(null);
    try {
      await chanakyaApi.orchestrate(runId);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Orchestration failed");
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async (personId: string, approve: boolean) => {
    try {
      await chanakyaApi.approveQaRecord(runId, personId, approve);
      const q = await chanakyaApi.listQaRecords(runId);
      setQaRecords(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record approval");
    }
  };

  const handleExport = async (format: "json" | "csv") => {
    try {
      const url = await chanakyaApi.exportBlobUrl(runId, format);
      window.open(url, "_blank");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  if (!run) {
    return <div className="text-center text-gray-500">{error || "Loading run..."}</div>;
  }

  const personById = new Map(people.map((p) => [p.id, p]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-display tracking-tight">Run: {run.period}</h1>
        <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      <Card className="p-4">
        <h2 className="mb-3 font-medium">Pipeline stages</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {run.agent_executions.map((e) => {
            const Icon = STAGE_ICONS[e.agent_name] ?? Gauge;
            const metric = stageMetric(e.agent_name, e.output_summary);
            const active = e.status === "running";
            return (
              <div
                key={e.agent_name}
                className={`rounded-lg border p-3 ${active ? "border-primary" : "border-[var(--stroke-muted)]"}`}
              >
                <div className="flex items-center gap-2">
                  <Icon size={16} strokeWidth={1.75} className="text-muted-foreground" />
                  <span className="text-xs font-medium">{STAGE_LABELS[e.agent_name] ?? e.agent_name}</span>
                </div>
                <div className="mt-2">
                  <Badge variant={statusVariant(e.status)} className="text-[11px]">
                    {e.status}
                    {e.retry_count > 0 ? ` (retry ${e.retry_count})` : ""}
                  </Badge>
                </div>
                {metric && <p className="mt-1 text-xs text-muted-foreground">{metric}</p>}
                {active && <div className="mt-2 h-0.5 animate-pulse rounded-full bg-primary" />}
              </div>
            );
          })}
        </div>
        {run.agent_executions
          .filter((e) => e.error)
          .map((e) => (
            <p key={e.agent_name} className="mt-3 text-xs text-red-600">
              {STAGE_LABELS[e.agent_name] ?? e.agent_name}: {e.error}
            </p>
          ))}
      </Card>

      {companies.length > 0 && (
        <Card className="space-y-3 p-4">
          <h2 className="font-medium">Funnel</h2>
          {[
            { label: "Companies found", value: companies.length, of: companies.length },
            { label: "Companies selected", value: companies.filter((c) => c.selected).length, of: companies.length },
            { label: "Leaders found", value: people.length, of: companies.length || 1 },
            { label: "Identity confirmed", value: people.filter((p) => p.identity_confirmed).length, of: people.length || 1 },
            { label: "QA approved", value: qaRecords.filter((q) => q.approval_status === "approved").length, of: qaRecords.length || 1 },
          ].map((row) => {
            const pct = row.of > 0 ? Math.round((row.value / row.of) * 100) : 0;
            return (
              <div key={row.label} className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{row.label}</span>
                  <span>{row.value}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </Card>
      )}

      <Card className="space-y-3 p-4">
        <h2 className="font-medium">1. Offering + ICP brief (Agent 01)</h2>
        <p className="text-sm text-gray-600">
          Multiple offerings may be submitted together — Company Scout searches once per ICP criterion
          across all of them. Each submission creates a new version; prior versions are never overwritten.
        </p>

        {offeringSnapshots.length > 0 && (() => {
          const latest = offeringSnapshots.reduce((a, b) => (b.version > a.version ? b : a));
          return (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Submitted catalogue (version {latest.version})
              </p>
              {latest.data.offerings.map((o, i) => (
                <div key={`${o.name}-${i}`} className="rounded-lg border p-3">
                  <p className="font-medium">{o.name}</p>
                  {o.description && <p className="text-sm text-muted-foreground">{o.description}</p>}
                  {o.icp_criteria && o.icp_criteria.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {o.icp_criteria.map((c) => (
                        <Badge key={c} variant="secondary">
                          {c}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          );
        })()}

        {offerings.filter((o) => o.name.trim()).length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Draft (not yet submitted)</p>
            {offerings
              .filter((o) => o.name.trim())
              .map((o, i) => (
                <div key={`${o.name}-${i}`} className="flex items-center justify-between rounded border px-3 py-1 text-sm">
                  <span>
                    {o.name}
                    {o.icp_criteria && o.icp_criteria.length > 0 ? ` — ${o.icp_criteria.join(", ")}` : ""}
                  </span>
                  <Button variant="outline" size="sm" onClick={() => handleRemoveOfferingRow(i)}>
                    Remove
                  </Button>
                </div>
              ))}
          </div>
        )}
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label htmlFor="offering-name">Offering name</Label>
            <Input
              id="offering-name"
              value={offeringName}
              onChange={(e) => setOfferingName(e.target.value)}
              placeholder="GenAI Accelerator"
              className="w-56"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="icp-criteria">ICP criteria (comma-separated)</Label>
            <Input
              id="icp-criteria"
              value={icpCriteria}
              onChange={(e) => setIcpCriteria(e.target.value)}
              placeholder="fintech, Series B"
              className="w-64"
            />
          </div>
          <Button variant="outline" onClick={handleAddOfferingRow} disabled={!offeringName}>
            Add offering
          </Button>
          <Button
            onClick={handleSubmitOffering}
            disabled={busy || offerings.filter((o) => o.name.trim()).length === 0}
          >
            Submit brief
          </Button>
        </div>
      </Card>

      <Card className="space-y-3 p-4">
        <h2 className="font-medium">2. Run Agents 02-07</h2>
        <p className="text-sm text-gray-600">
          Runs Company Scout through QA &amp; Sync in order. Safe to click again — completed stages are
          skipped, and a failed stage resumes from where it stopped.
        </p>
        <Button onClick={handleOrchestrate} disabled={busy}>
          {busy ? "Running..." : "Orchestrate run"}
        </Button>
      </Card>

      {companies.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-3 font-medium">Companies ({companies.length})</h2>
          <div className="space-y-1 text-sm">
            {companies.map((c) => (
              <div key={c.id} className="flex items-center justify-between border-b py-1 last:border-0">
                <span>
                  {c.name} <span className="text-gray-500">({c.domain})</span>
                </span>
                <span className="text-gray-500">fit {c.fit_score.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {people.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-3 font-medium">People ({people.length})</h2>
          <div className="space-y-1 text-sm">
            {people.map((p) => (
              <div key={p.id} className="flex items-center justify-between border-b py-1 last:border-0">
                <span>
                  {p.full_name} — {p.role}
                </span>
                <Badge variant={p.identity_confirmed ? "default" : "secondary"}>{p.resolution_status}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {needsReview.length > 0 && (
        <Card className="space-y-3 p-4">
          <h2 className="font-medium">LinkedIn identity review queue ({needsReview.length})</h2>
          <p className="text-sm text-gray-600">
            Zero or multiple search matches — Agent 04 could not confirm automatically. Review the
            candidate profiles found and paste the correct LinkedIn URL, or leave unresolved.
          </p>
          <div className="space-y-3">
            {needsReview.map((person) => (
              <div key={person.id} className="rounded-lg border p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {person.full_name} — {person.role}
                  </span>
                  <Badge variant="secondary">{person.resolution_status}</Badge>
                </div>
                {person.candidate_profiles.length > 0 && (
                  <ul className="mt-2 space-y-1 text-sm text-gray-600">
                    {person.candidate_profiles.map((c) => (
                      <li key={c.linkedin_url}>
                        <a
                          href={c.linkedin_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {c.title ?? c.linkedin_url}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-2 flex items-end gap-2">
                  <Input
                    placeholder="https://linkedin.com/in/correct-profile"
                    value={resolveUrls[person.id] ?? ""}
                    onChange={(e) =>
                      setResolveUrls((prev) => ({ ...prev, [person.id]: e.target.value }))
                    }
                    className="w-80"
                  />
                  <Button size="sm" onClick={() => handleResolveManually(person.id)}>
                    Confirm
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {emails.length > 0 && (
        <Card className="p-4">
          <h2 className="mb-3 font-medium">Email candidates ({emails.length})</h2>
          <div className="space-y-1 text-sm">
            {emails.map((e) => (
              <div key={e.id} className="flex items-center justify-between border-b py-1 last:border-0">
                <span>{e.email}</span>
                <Badge variant={e.verification_status === "valid" ? "default" : "secondary"}>
                  {e.verification_status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {qaRecords.length > 0 && (
        <Card className="space-y-3 p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">QA &amp; approval ({qaRecords.length})</h2>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => handleExport("json")}>
                Export JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("csv")}>
                Export CSV
              </Button>
            </div>
          </div>
          <div className="space-y-3">
            {qaRecords.map((record) => {
              const person = personById.get(record.person_id);
              return (
                <div key={record.id} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{person?.full_name ?? record.person_id}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={record.confidence_level === "high" ? "default" : "secondary"}>
                        {record.confidence_level}
                      </Badge>
                      <Badge
                        variant={
                          record.approval_status === "approved"
                            ? "default"
                            : record.approval_status === "rejected"
                              ? "destructive"
                              : "secondary"
                        }
                      >
                        {record.approval_status}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-2 text-sm font-medium">{record.draft_subject}</p>
                  <p className="whitespace-pre-wrap text-sm text-gray-600">{record.draft_body}</p>
                  {record.approval_status === "pending_review" && (
                    <div className="mt-2 flex gap-2">
                      <Button size="sm" onClick={() => handleApprove(record.person_id, true)}>
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleApprove(record.person_id, false)}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
