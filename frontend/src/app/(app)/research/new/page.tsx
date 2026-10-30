import { PlusCircle } from "lucide-react";

import { EmptyState } from "@/components/empty-state";

export default function NewResearchPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">New Research</h1>
      <EmptyState
        icon={PlusCircle}
        title="Research intake form coming in Phase 1"
        description="LinkedIn URL, name + company, paste/upload, and PDF intake land here next."
      />
    </div>
  );
}
