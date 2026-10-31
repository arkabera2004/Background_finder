"use client";

import { Building2, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState({ prospects: 0, companies: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [prospects, companies] = await Promise.all([
          api.listProspects(),
          api.listCompanies(),
        ]);
        setStats({ prospects: prospects.length, companies: companies.length });
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-display tracking-tight">Dashboard</h1>

      {loading ? (
        <div className="text-center text-gray-500">Loading stats...</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <Card className="p-6">
            <div className="flex items-center space-x-4">
              <Users className="h-8 w-8 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-gray-600">Prospects</p>
                <p className="text-2xl font-bold">{stats.prospects}</p>
              </div>
            </div>
          </Card>
          <Card className="p-6">
            <div className="flex items-center space-x-4">
              <Building2 className="h-8 w-8 text-green-600" />
              <div>
                <p className="text-sm font-medium text-gray-600">Companies</p>
                <p className="text-2xl font-bold">{stats.companies}</p>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
