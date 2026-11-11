"use client";

import { Building2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ChanakyaSubNav } from "@/components/chanakya-sub-nav";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { chanakyaApi, type ScoutedCompanyView } from "@/lib/chanakya-api";

type TabKey = "all" | "high-fit" | "selected";

const HIGH_FIT_THRESHOLD = 0.7;

function FitScoreBar({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="w-10 text-right text-sm tabular-nums">{pct}</span>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ChanakyaCompaniesPage() {
  const [companies, setCompanies] = useState<ScoutedCompanyView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<TabKey>("all");

  useEffect(() => {
    chanakyaApi
      .listAllCompanies()
      .then(setCompanies)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load companies"))
      .finally(() => setLoading(false));
  }, []);

  const highFitCount = companies.filter((c) => c.fit_score >= HIGH_FIT_THRESHOLD).length;
  const selectedCount = companies.filter((c) => c.selected).length;

  const visible = useMemo(() => {
    let rows = companies;
    if (tab === "high-fit") rows = rows.filter((c) => c.fit_score >= HIGH_FIT_THRESHOLD);
    if (tab === "selected") rows = rows.filter((c) => c.selected);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((c) => c.name.toLowerCase().includes(q) || c.domain.toLowerCase().includes(q));
    }
    return [...rows].sort((a, b) => b.fit_score - a.fit_score);
  }, [companies, tab, search]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-tight">Chanakya — GTM Prospecting Engine</h1>
        <ChanakyaSubNav />
      </div>

      <div>
        <h2 className="text-lg font-medium">Companies</h2>
        <p className="text-sm text-muted-foreground">
          Every company any monthly run has scouted, across all periods, ranked by fit score.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex gap-1 border-b border-[var(--stroke-muted)]" aria-label="Company filters">
          {(
            [
              ["all", `All companies ${companies.length}`],
              ["high-fit", `High fit, 70+ ${highFitCount}`],
              ["selected", `Selected ${selectedCount}`],
            ] as [TabKey, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={
                tab === key
                  ? "border-b-2 border-primary px-3 py-2 text-sm font-medium text-foreground"
                  : "border-b-2 border-transparent px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
              }
            >
              {label}
            </button>
          ))}
        </nav>
        <Input
          placeholder="Search company or domain"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64"
        />
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-500">Loading companies...</div>
      ) : visible.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No companies yet"
          description="Run Company Scout on a monthly run to populate this list."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <div className="grid grid-cols-[2fr_1fr_1fr] gap-4 border-b bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground">
            <span>Company</span>
            <span>Fit score</span>
            <span>Status</span>
          </div>
          {visible.map((c) => (
            <a
              key={c.id}
              href={c.source_url}
              target="_blank"
              rel="noreferrer"
              className="grid grid-cols-[2fr_1fr_1fr] items-center gap-4 border-b px-4 py-3 text-sm last:border-0 hover:bg-muted/30"
            >
              <span>
                <span className="font-medium">{c.name}</span>{" "}
                <span className="text-muted-foreground">({c.domain})</span>
              </span>
              <FitScoreBar score={c.fit_score} />
              <Badge variant={c.selected ? "default" : "secondary"}>
                {c.selected ? "selected" : "scored"}
              </Badge>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
