"use client";

import { Building2, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, type Company } from "@/lib/api";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCompanies = async () => {
      try {
        const data = await api.listCompanies();
        setCompanies(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load companies");
      } finally {
        setLoading(false);
      }
    };

    loadCompanies();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this company?")) return;

    try {
      await api.deleteCompany(id);
      setCompanies(companies.filter((c) => c.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete company");
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Companies</h1>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="text-center text-gray-500">Loading companies...</div>
      ) : companies.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No companies yet"
          description="Companies get added automatically as you research prospects at them."
        />
      ) : (
        <div className="space-y-2">
          {companies.map((company) => (
            <Card key={company.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <Link
                    href={`/companies/${company.id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {company.name}
                  </Link>
                  {company.domain && <p className="text-sm text-gray-600">{company.domain}</p>}
                  <p className="text-xs text-gray-500">{new Date(company.created_at).toLocaleDateString()}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(company.id)}
                  className="text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
