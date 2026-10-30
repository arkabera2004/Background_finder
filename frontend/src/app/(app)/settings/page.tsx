"use client";

import { useQuery } from "@tanstack/react-query";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {isLoading && <Skeleton className="h-4 w-48" />}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                Could not reach the API at NEXT_PUBLIC_API_URL. Is the backend running?
              </AlertDescription>
            </Alert>
          )}
          {data && (
            <>
              <p>
                <span className="text-muted-foreground">User ID: </span>
                {data.id}
              </p>
              <p>
                <span className="text-muted-foreground">Email: </span>
                {data.email}
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
