import { Users } from "lucide-react";

import { EmptyState } from "@/components/empty-state";

export default function ProspectsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Prospects</h1>
      <EmptyState
        icon={Users}
        title="No prospects yet"
        description="Prospects you research will show up here, searchable and filterable."
        actionLabel="New Research"
        actionHref="/research/new"
      />
    </div>
  );
}
