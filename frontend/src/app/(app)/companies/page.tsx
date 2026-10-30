import { Building2 } from "lucide-react";

import { EmptyState } from "@/components/empty-state";

export default function CompaniesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Companies</h1>
      <EmptyState
        icon={Building2}
        title="No companies yet"
        description="Companies get added automatically as you research prospects at them."
      />
    </div>
  );
}
