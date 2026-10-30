import { LayoutDashboard } from "lucide-react";

import { EmptyState } from "@/components/empty-state";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <EmptyState
        icon={LayoutDashboard}
        title="No research yet"
        description="Run your first prospect research to see stats here."
        actionLabel="New Research"
        actionHref="/research/new"
      />
    </div>
  );
}
