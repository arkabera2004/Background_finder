"use client";

import { Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ChanakyaSubNav } from "@/components/chanakya-sub-nav";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { chanakyaApi, type PersonView } from "@/lib/chanakya-api";

type TabKey = "all" | "confirmed" | "needs-review";

function resolutionVariant(status: PersonView["resolution_status"]): "default" | "secondary" | "destructive" {
  if (status === "confirmed") return "default";
  if (status === "unresolved") return "destructive";
  return "secondary";
}

export default function ChanakyaPeoplePage() {
  const [people, setPeople] = useState<PersonView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<TabKey>("all");

  useEffect(() => {
    chanakyaApi
      .listAllPeople()
      .then(setPeople)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load leaders"))
      .finally(() => setLoading(false));
  }, []);

  const confirmedCount = people.filter((p) => p.identity_confirmed).length;
  const needsReviewCount = people.filter((p) => p.resolution_status === "ambiguous" || p.resolution_status === "unresolved").length;

  const visible = useMemo(() => {
    let rows = people;
    if (tab === "confirmed") rows = rows.filter((p) => p.identity_confirmed);
    if (tab === "needs-review") {
      rows = rows.filter((p) => p.resolution_status === "ambiguous" || p.resolution_status === "unresolved");
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(
        (p) => p.full_name.toLowerCase().includes(q) || (p.company_name ?? "").toLowerCase().includes(q),
      );
    }
    return [...rows].sort((a, b) => b.confidence - a.confidence);
  }, [people, tab, search]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-tight">Chanakya — GTM Prospecting Engine</h1>
        <ChanakyaSubNav />
      </div>

      <div>
        <h2 className="text-lg font-medium">Leaders</h2>
        <p className="text-sm text-muted-foreground">
          Every decision-maker any monthly run has found, across all periods.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex gap-1 border-b border-[var(--stroke-muted)]" aria-label="Leader filters">
          {(
            [
              ["all", `All leaders ${people.length}`],
              ["confirmed", `Confirmed ${confirmedCount}`],
              ["needs-review", `Needs review ${needsReviewCount}`],
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
          placeholder="Search name or company"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64"
        />
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-500">Loading leaders...</div>
      ) : visible.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No leaders yet"
          description="Run People Finder on a monthly run to populate this list."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <div className="hidden gap-4 border-b bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground sm:grid sm:grid-cols-[2fr_2fr_1fr_1fr]">
            <span>Name</span>
            <span>Company</span>
            <span>Role</span>
            <span>Identity</span>
          </div>
          {visible.map((p) => (
            <div
              key={p.id}
              className="grid grid-cols-1 items-start gap-1 border-b px-4 py-3 text-sm last:border-0 sm:grid-cols-[2fr_2fr_1fr_1fr] sm:items-center sm:gap-4"
            >
              <span className="font-medium">
                {p.linkedin_url ? (
                  <a href={p.linkedin_url} target="_blank" rel="noreferrer" className="hover:underline">
                    {p.full_name}
                  </a>
                ) : (
                  p.full_name
                )}
              </span>
              <span className="text-muted-foreground">{p.company_name ?? "—"}</span>
              <span>{p.role}</span>
              <Badge variant={resolutionVariant(p.resolution_status)}>{p.resolution_status}</Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
