"use client";

import { Link2, Mail, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { ChanakyaSubNav } from "@/components/chanakya-sub-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  chanakyaApi,
  type EmailCandidateView,
  type PersonView,
  type QARecordView,
} from "@/lib/chanakya-api";

function QueueEmptyState({ icon: Icon, label }: { icon: typeof Mail; label: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center text-muted-foreground">
      <Icon size={24} strokeWidth={1.5} />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export default function ChanakyaNeedsYouPage() {
  const [linkedinLookups, setLinkedinLookups] = useState<PersonView[]>([]);
  const [riskyEmails, setRiskyEmails] = useState<EmailCandidateView[]>([]);
  const [lowConfidence, setLowConfidence] = useState<QARecordView[]>([]);
  const [resolveUrls, setResolveUrls] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAll = () => {
    Promise.all([
      chanakyaApi.listAllPeopleNeedingReview(),
      chanakyaApi.listRiskyEmails(),
      chanakyaApi.listLowConfidenceContacts(),
    ])
      .then(([people, emails, qa]) => {
        setLinkedinLookups(people);
        setRiskyEmails(emails);
        setLowConfidence(qa);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load review queues"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleResolve = async (person: PersonView) => {
    const url = resolveUrls[person.id];
    if (!url) return;
    try {
      await chanakyaApi.resolvePersonManually(person.run_id, person.id, url);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve identity");
    }
  };

  const handleApprove = async (record: QARecordView, approve: boolean) => {
    try {
      await chanakyaApi.approveQaRecord(record.run_id, record.person_id, approve);
      loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record decision");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-tight">Chanakya — GTM Prospecting Engine</h1>
        <ChanakyaSubNav />
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">Needs you</h2>
          <p className="text-sm text-muted-foreground">
            {linkedinLookups.length + riskyEmails.length + lowConfidence.length} items the agents could
            not finish. Nothing for these contacts goes out until you decide.
          </p>
        </div>
        <div className="flex gap-2">
          <Badge variant="secondary">{linkedinLookups.length} LinkedIn lookups</Badge>
          <Badge variant="secondary">{lowConfidence.length} low confidence</Badge>
          <Badge variant="secondary">{riskyEmails.length} risky emails</Badge>
        </div>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}
      {loading && <div className="text-center text-gray-500">Loading review queues...</div>}

      {!loading && (
        <>
          <Card className="space-y-3 p-4">
            <div className="flex items-center justify-between">
              <h3 className="flex items-center gap-2 font-medium">
                <Link2 size={16} /> Manual LinkedIn lookups ({linkedinLookups.length})
              </h3>
              <span className="text-xs text-muted-foreground">Paste the profile URL, or drop the person.</span>
            </div>
            {linkedinLookups.length === 0 ? (
              <QueueEmptyState icon={Link2} label="Nothing in the queue." />
            ) : (
              <div className="space-y-2">
                {linkedinLookups.map((p) => (
                  <div key={p.id} className="flex items-center justify-between gap-3 rounded border p-3">
                    <div>
                      <p className="font-medium">
                        {p.full_name} — {p.role}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {p.company_name ?? "—"} · {p.resolution_status}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        placeholder="https://linkedin.com/in/..."
                        value={resolveUrls[p.id] ?? ""}
                        onChange={(e) => setResolveUrls((prev) => ({ ...prev, [p.id]: e.target.value }))}
                        className="w-64"
                      />
                      <Button size="sm" onClick={() => handleResolve(p)}>
                        Confirm
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="space-y-3 p-4">
            <h3 className="flex items-center gap-2 font-medium">
              <ShieldAlert size={16} /> Low-confidence contacts ({lowConfidence.length})
            </h3>
            <p className="text-xs text-muted-foreground">Fix the email or LinkedIn, or drop.</p>
            {lowConfidence.length === 0 ? (
              <QueueEmptyState icon={ShieldAlert} label="Nothing to review." />
            ) : (
              <div className="space-y-2">
                {lowConfidence.map((q) => (
                  <div key={q.id} className="flex items-center justify-between gap-3 rounded border p-3">
                    <div>
                      <p className="font-medium">{q.person_name ?? q.person_id}</p>
                      <p className="text-xs text-muted-foreground">
                        {q.confidence_level} confidence · {q.draft_subject}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleApprove(q, true)}>
                        Approve
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleApprove(q, false)}>
                        Reject
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="space-y-3 p-4">
            <h3 className="flex items-center gap-2 font-medium">
              <Mail size={16} /> Risky emails ({riskyEmails.length})
            </h3>
            <p className="text-xs text-muted-foreground">Pattern guess on a live mail domain. Not confirmed.</p>
            {riskyEmails.length === 0 ? (
              <QueueEmptyState icon={Mail} label="No risky emails waiting." />
            ) : (
              <div className="space-y-1">
                {riskyEmails.map((e) => (
                  <div key={e.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
                    <span>
                      {e.person_name ?? e.person_id} — {e.email}
                    </span>
                    <span className="text-xs text-muted-foreground">{e.pattern}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
