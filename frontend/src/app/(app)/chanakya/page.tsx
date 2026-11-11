"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ChanakyaSubNav } from "@/components/chanakya-sub-nav";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { chanakyaApi, type MonthlyRun } from "@/lib/chanakya-api";

function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function ChanakyaPage() {
  const [runs, setRuns] = useState<MonthlyRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState(currentPeriod());
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const loadRuns = async () => {
      try {
        setRuns(await chanakyaApi.listRuns());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load runs");
      } finally {
        setLoading(false);
      }
    };
    loadRuns();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      await chanakyaApi.createRun(period);
      setRuns(await chanakyaApi.listRuns());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create run");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-tight">Chanakya — GTM Prospecting Engine</h1>
        <ChanakyaSubNav />
      </div>

      <Card className="flex items-end gap-3 p-4">
        <div className="space-y-1">
          <Label htmlFor="period">Period (YYYY-MM)</Label>
          <Input id="period" value={period} onChange={(e) => setPeriod(e.target.value)} className="w-40" />
        </div>
        <Button onClick={handleCreate} disabled={creating}>
          {creating ? "Creating..." : "New monthly run"}
        </Button>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="text-center text-gray-500">Loading runs...</div>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No monthly runs yet"
          description="Create a run above, then submit an offering brief and orchestrate the seven agents."
        />
      ) : (
        <div className="space-y-2">
          {runs.map((run) => (
            <Card key={run.id} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <Link href={`/chanakya/${run.id}`} className="font-medium text-blue-600 hover:underline">
                    {run.period}
                  </Link>
                  <p className="text-xs text-gray-500">{new Date(run.created_at).toLocaleString()}</p>
                </div>
                <Badge variant={run.status === "completed" ? "default" : "secondary"}>{run.status}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
