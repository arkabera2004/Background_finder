"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type RunView } from "@/lib/api";

const STAGE_LABELS: Record<string, string> = {
  resolve_identity: "Resolve Identity",
  fetch_profile: "Fetch Profile",
  analyse_career: "Analyse Career",
  research_company: "Research Company",
  analyse_activity: "Analyse Activity",
  web_footprint: "Web Footprint",
  synthesise_brief: "Synthesise Brief",
};

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "completed"
      ? "default"
      : status === "failed"
        ? "destructive"
        : status === "running"
          ? "secondary"
          : "outline";
  return <Badge variant={variant}>{status}</Badge>;
}

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const runId = params.id;

  const { data: run, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: (query) => {
      const data = query.state.data as RunView | undefined;
      return data && TERMINAL.has(data.status) ? false : 1000;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelRun(runId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["run", runId] }),
  });

  const retryMutation = useMutation({
    mutationFn: () => api.retryRun(runId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["run", runId] }),
  });

  if (isLoading || !run) {
    return (
      <div className="max-w-2xl space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Research Run</h1>
        <StatusBadge status={run.status} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {Object.entries(run.steps).map(([stage, step]) => (
            <div key={stage} className="flex items-center justify-between text-sm">
              <span>{STAGE_LABELS[stage] ?? stage}</span>
              <div className="flex items-center gap-2">
                {step.error && (
                  <span className="text-xs text-destructive" title={step.error}>
                    error
                  </span>
                )}
                <StatusBadge status={step.status} />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {run.status === "running" && (
        <Button variant="outline" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>
          Cancel Run
        </Button>
      )}

      {run.status === "failed" && (
        <Button onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
          Retry
        </Button>
      )}

      {run.status === "completed" && run.brief && (
        <Card>
          <CardHeader>
            <CardTitle>Prospect Brief: {String(run.brief.prospect_name)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Alert>
              <AlertDescription>
                This brief was synthesised without web search or AI synthesis
                credentials configured, so it only contains what was directly
                supplied — no fabricated claims. See the sources list for
                exactly what backs each claim.
              </AlertDescription>
            </Alert>
            <Button variant="outline" size="sm" onClick={() => router.push(`/prospects`)}>
              View in Prospect Library
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
