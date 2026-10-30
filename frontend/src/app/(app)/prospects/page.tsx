"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Users } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function ProspectsPage() {
  const { data: prospects, isLoading } = useQuery({
    queryKey: ["prospects"],
    queryFn: api.listProspects,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Prospects</h1>

      {isLoading && <Skeleton className="h-24 w-full" />}

      {!isLoading && (!prospects || prospects.length === 0) && (
        <EmptyState
          icon={Users}
          title="No saved prospects yet"
          description="Run research and explicitly save the result to build your library."
          actionLabel="New Research"
          actionHref="/research/new"
        />
      )}

      {prospects && prospects.length > 0 && (
        <div className="space-y-2">
          {prospects.map((p) => (
            <Link key={p.id} href={`/prospects/${p.id}`}>
              <Card className="transition-colors hover:bg-muted/50">
                <CardContent className="flex items-center justify-between py-4">
                  <div>
                    <p className="font-medium">{p.full_name}</p>
                    <p className="text-sm text-muted-foreground">
                      Saved {new Date(p.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Badge variant="outline">{p.status}</Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
