"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ExportFormat } from "@/lib/api";

export default function ProspectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id;

  const { data: prospect, isLoading } = useQuery({
    queryKey: ["prospect", id],
    queryFn: () => api.getProspect(id),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteProspect(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prospects"] });
      router.push("/prospects");
    },
  });

  async function handleExport(format: ExportFormat) {
    const url = await api.exportBriefUrl(id, format);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${prospect?.full_name ?? "brief"}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading || !prospect) {
    return (
      <div className="max-w-2xl space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const brief = prospect.brief as Record<string, unknown> | null;
  const sources = (brief?.sources as Array<{ id: string; url: string; title?: string }>) ?? [];

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{prospect.full_name}</h1>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
        >
          Delete
        </Button>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={() => handleExport("json")}>
          Export JSON
        </Button>
        <Button variant="outline" size="sm" onClick={() => handleExport("md")}>
          Export Markdown
        </Button>
        <Button variant="outline" size="sm" onClick={() => handleExport("pdf")}>
          Export PDF
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Sources ({sources.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {sources.length === 0 && (
            <p className="text-muted-foreground">
              No web sources — this brief was built from directly supplied
              information only.
            </p>
          )}
          {sources.map((s) => (
            <a
              key={s.id}
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="block text-primary hover:underline"
            >
              {s.title ?? s.url}
            </a>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
