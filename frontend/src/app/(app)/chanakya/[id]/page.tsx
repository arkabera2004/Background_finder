"use client";

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

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "completed") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

export default function ChanakyaRunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [run, setRun] = useState<MonthlyRun | null>(null);
  const [companies, setCompanies] = useState<ScoutedCompanyView[]>([]);
  const [people, setPeople] = useState<PersonView[]>([]);
  const [emails, setEmails] = useState<EmailCandidateView[]>([]);
  const [qaRecords, setQaRecords] = useState<QARecordView[]>([]);
  const [offeringName, setOfferingName] = useState("");
  const [icpCriteria, setIcpCriteria] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadAll = async () => {
    try {
      const r = await chanakyaApi.getRun(runId);
      setRun(r);
      const [c, p, e, q] = await Promise.all([
        chanakyaApi.listCompanies(runId).catch(() => []),
        chanakyaApi.listPeople(runId).catch(() => []),
        chanakyaApi.listEmails(runId).catch(() => []),
        chanakyaApi.listQaRecords(runId).catch(() => []),
      ]);
      setCompanies(c);
      setPeople(p);
      setEmails(e);
      setQaRecords(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load, not a cascading update
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const handleSubmitOffering = async () => {
    setBusy(true);
    setError(null);
    try {
      await chanakyaApi.submitOfferings(runId, [
        {
          name: offeringName,
          icp_criteria: icpCriteria
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        },
      ]);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit offering brief");
    } finally {
      setBusy(false);
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
        <div className="flex flex-wrap gap-2">
          {run.agent_executions.map((e) => (
            <Badge key={e.agent_name} variant={statusVariant(e.status)}>
              {STAGE_LABELS[e.agent_name] ?? e.agent_name}: {e.status}
            </Badge>
          ))}
        </div>
      </Card>

      <Card className="space-y-3 p-4">
        <h2 className="font-medium">1. Offering + ICP brief (Agent 01)</h2>
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
          <Button onClick={handleSubmitOffering} disabled={busy || !offeringName}>
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
