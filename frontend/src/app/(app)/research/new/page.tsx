"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, type ResearchDepth } from "@/lib/api";

type IntakeMethod = "url" | "name_company" | "paste";

export default function NewResearchPage() {
  const router = useRouter();
  const [method, setMethod] = useState<IntakeMethod>("url");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("standard");

  const mutation = useMutation({
    mutationFn: () =>
      api.createResearch({
        depth,
        ...(method === "url" ? { linkedin_url: linkedinUrl } : {}),
        ...(method === "name_company" ? { full_name: fullName, company } : {}),
        ...(method === "paste" ? { full_name: fullName, pasted_text: pastedText } : {}),
      }),
    onSuccess: (data) => {
      router.push(`/runs/${data.run_id}`);
    },
  });

  const errorMessage =
    mutation.error instanceof ApiError
      ? (() => {
          try {
            const parsed = JSON.parse(mutation.error.message);
            return Array.isArray(parsed.detail)
              ? parsed.detail.map((d: { msg: string }) => d.msg).join(", ")
              : parsed.detail ?? mutation.error.message;
          } catch {
            return mutation.error.message;
          }
        })()
      : mutation.error
        ? "Something went wrong submitting this research request."
        : null;

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-xl font-display tracking-tight">New Research</h1>
      <Card>
        <CardHeader>
          <CardTitle>How should we find this person?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            {(
              [
                ["url", "LinkedIn URL"],
                ["name_company", "Name + Company"],
                ["paste", "Paste Profile Text"],
              ] as const
            ).map(([value, label]) => (
              <Button
                key={value}
                type="button"
                size="sm"
                variant={method === value ? "default" : "outline"}
                onClick={() => setMethod(value)}
              >
                {label}
              </Button>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
            className="space-y-3"
          >
            {method === "url" && (
              <div className="space-y-1">
                <Label htmlFor="linkedin_url">LinkedIn profile URL</Label>
                <Input
                  id="linkedin_url"
                  placeholder="https://linkedin.com/in/username"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  required
                />
              </div>
            )}

            {method === "name_company" && (
              <>
                <div className="space-y-1">
                  <Label htmlFor="full_name">Full name</Label>
                  <Input
                    id="full_name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="company">Company</Label>
                  <Input
                    id="company"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    required
                  />
                </div>
                <Alert>
                  <AlertDescription>
                    Without a configured search provider, this will resolve the
                    person&apos;s identity directly from what you entered rather
                    than finding candidate matches.
                  </AlertDescription>
                </Alert>
              </>
            )}

            {method === "paste" && (
              <>
                <div className="space-y-1">
                  <Label htmlFor="paste_name">Full name</Label>
                  <Input
                    id="paste_name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="pasted_text">Pasted profile text (min 50 characters)</Label>
                  <textarea
                    id="pasted_text"
                    className="w-full min-h-32 rounded-md border border-input bg-background p-2 text-sm"
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                    required
                    minLength={50}
                  />
                </div>
              </>
            )}

            <div className="space-y-1">
              <Label htmlFor="depth">Research depth</Label>
              <select
                id="depth"
                className="w-full rounded-md border border-input bg-background p-2 text-sm"
                value={depth}
                onChange={(e) => setDepth(e.target.value as ResearchDepth)}
              >
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </select>
            </div>

            {errorMessage && (
              <Alert variant="destructive">
                <AlertDescription>{errorMessage}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" disabled={mutation.isPending} className="w-full">
              {mutation.isPending ? "Starting research..." : "Start Research"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
