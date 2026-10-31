"use client";

import { ArrowLeft, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, type Company } from "@/lib/api";

export default function CompanyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (!id) return;

    const loadCompany = async () => {
      try {
        const data = await api.getCompany(id);
        setCompany(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load company");
      } finally {
        setLoading(false);
      }
    };

    loadCompany();
  }, [id]);

  const handleDelete = async () => {
    if (!company || !confirm("Are you sure you want to delete this company?")) return;

    try {
      await api.deleteCompany(company.id);
      router.push("/companies");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete company");
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="text-center text-gray-500">Loading company...</div>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="space-y-6">
        <Link href="/companies">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error || "Company not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link href="/companies">
        <Button variant="ghost" size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display tracking-tight">{company.name}</h1>
          {company.domain && <p className="text-gray-600">{company.domain}</p>}
        </div>
        <Button variant="destructive" size="sm" onClick={handleDelete}>
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </Button>
      </div>

      {Object.keys(company.data || {}).length > 0 && (
        <Card className="p-6">
          <h2 className="mb-4 font-semibold">Research Data</h2>
          <dl className="space-y-2">
            {Object.entries(company.data || {}).map(([key, value]) => (
              <div key={key} className="text-sm">
                <dt className="font-medium text-gray-700">{key}</dt>
                <dd className="text-gray-600">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      <Card className="p-6">
        <h2 className="mb-4 font-semibold">Metadata</h2>
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="font-medium text-gray-700">Created</dt>
            <dd className="text-gray-600">{new Date(company.created_at).toLocaleString()}</dd>
          </div>
          {company.crawled_at && (
            <div>
              <dt className="font-medium text-gray-700">Last Crawled</dt>
              <dd className="text-gray-600">{new Date(company.crawled_at).toLocaleString()}</dd>
            </div>
          )}
        </dl>
      </Card>
    </div>
  );
}
