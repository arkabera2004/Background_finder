"use client";

import { Plug } from "lucide-react";
import { useEffect, useState } from "react";

import { ChanakyaSubNav } from "@/components/chanakya-sub-nav";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { chanakyaApi, type IntegrationStatus } from "@/lib/chanakya-api";

function statusVariant(status: IntegrationStatus["status"]): "default" | "secondary" {
  return status === "active" ? "default" : "secondary";
}

export default function ChanakyaIntegrationsPage() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    chanakyaApi
      .listIntegrations()
      .then(setIntegrations)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load integrations"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-tight">Chanakya — GTM Prospecting Engine</h1>
        <ChanakyaSubNav />
      </div>

      <div>
        <h2 className="text-lg font-medium">Integrations and schedule</h2>
        <p className="text-sm text-muted-foreground">
          The tools Chanakya runs on, and the real state of each — never a secret value.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-500">Loading integrations...</div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {integrations.map((p) => (
            <Card key={p.name} className="space-y-2 p-4">
              <div className="flex items-center gap-2">
                <Plug size={16} className="text-muted-foreground" />
                <span className="font-medium">{p.name}</span>
              </div>
              <p className="text-xs text-muted-foreground">{p.purpose}</p>
              <Badge variant={statusVariant(p.status)}>{p.status}</Badge>
              <p className="text-xs text-muted-foreground">{p.note}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
