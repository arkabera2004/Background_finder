"use client";

import { CalendarClock } from "lucide-react";
import { useEffect, useState } from "react";

import { ChanakyaSubNav } from "@/components/chanakya-sub-nav";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { chanakyaApi, type ChanakyaSchedule } from "@/lib/chanakya-api";

export default function ChanakyaSchedulesPage() {
  const [schedules, setSchedules] = useState<ChanakyaSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offeringName, setOfferingName] = useState("");
  const [icpCriteria, setIcpCriteria] = useState("");
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    try {
      setSchedules(await chanakyaApi.listSchedules());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load, not a cascading update
    load();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      await chanakyaApi.createSchedule({
        offerings: [
          {
            name: offeringName,
            icp_criteria: icpCriteria
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          },
        ],
        day_of_month: dayOfMonth,
      });
      setOfferingName("");
      setIcpCriteria("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create schedule");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (schedule: ChanakyaSchedule) => {
    try {
      await chanakyaApi.setScheduleEnabled(schedule.id, !schedule.enabled);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update schedule");
    }
  };

  const handleDelete = async (scheduleId: string) => {
    try {
      await chanakyaApi.deleteSchedule(scheduleId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete schedule");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-tight">Chanakya — GTM Prospecting Engine</h1>
        <ChanakyaSubNav />
      </div>
      <p className="text-sm text-muted-foreground">
        A schedule auto-triggers the full seven-agent pipeline every month on the chosen day, for the
        offering/ICP brief stored here — no manual &quot;New monthly run&quot; click needed. A manual run always
        remains available regardless of schedules.
      </p>

      <Card className="space-y-3 p-4">
        <h2 className="font-medium">New schedule</h2>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label htmlFor="sched-offering-name">Offering name</Label>
            <Input
              id="sched-offering-name"
              value={offeringName}
              onChange={(e) => setOfferingName(e.target.value)}
              placeholder="GenAI Accelerator"
              className="w-56"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sched-icp-criteria">ICP criteria (comma-separated)</Label>
            <Input
              id="sched-icp-criteria"
              value={icpCriteria}
              onChange={(e) => setIcpCriteria(e.target.value)}
              placeholder="fintech, Series B"
              className="w-64"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sched-day">Day of month</Label>
            <Input
              id="sched-day"
              type="number"
              min={1}
              max={28}
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(Number(e.target.value))}
              className="w-24"
            />
          </div>
          <Button onClick={handleCreate} disabled={creating || !offeringName}>
            {creating ? "Creating..." : "Create schedule"}
          </Button>
        </div>
      </Card>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-500">Loading schedules...</div>
      ) : schedules.length === 0 ? (
        <EmptyState
          icon={CalendarClock}
          title="No schedules yet"
          description="Create one above to have the pipeline run automatically every month."
        />
      ) : (
        <div className="space-y-2">
          {schedules.map((schedule) => (
            <Card key={schedule.id} className="space-y-2 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">
                    {schedule.offerings.map((o) => o.name).join(", ")}
                  </p>
                  <p className="text-xs text-gray-500">
                    Day {schedule.day_of_month} of each month
                    {schedule.last_run_period ? ` — last ran ${schedule.last_run_period}` : " — never run yet"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={schedule.enabled ? "default" : "secondary"}>
                    {schedule.enabled ? "enabled" : "disabled"}
                  </Badge>
                  {schedule.last_run_status && (
                    <Badge variant={schedule.last_run_status === "failed" ? "destructive" : "secondary"}>
                      last run: {schedule.last_run_status}
                    </Badge>
                  )}
                </div>
              </div>
              {schedule.last_run_error && (
                <p className="text-xs text-red-600">{schedule.last_run_error}</p>
              )}
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleToggle(schedule)}>
                  {schedule.enabled ? "Disable" : "Enable"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDelete(schedule.id)}>
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
