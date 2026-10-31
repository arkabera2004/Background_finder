import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { BriefClaim, BriefHook, BriefSource, ProspectBrief } from "@/lib/api";

const SECTIONS: { key: keyof ProspectBrief; label: string }[] = [
  { key: "snapshot", label: "Snapshot" },
  { key: "career_story", label: "Career Story" },
  { key: "current_role", label: "Current Role" },
  { key: "company", label: "Company" },
  { key: "content_and_interests", label: "Content & Interests" },
  { key: "communication_style", label: "Communication Style" },
  { key: "likely_priorities", label: "Likely Priorities" },
];

function confidenceVariant(confidence: string): "default" | "secondary" | "outline" {
  if (confidence === "high") return "default";
  if (confidence === "medium") return "secondary";
  return "outline";
}

function SourceRefs({ ids, sourcesById }: { ids: string[]; sourcesById: Map<string, BriefSource> }) {
  if (ids.length === 0) return null;
  return (
    <span className="ml-1 space-x-1">
      {ids.map((id) => {
        const source = sourcesById.get(id);
        if (!source) return null;
        return (
          <a
            key={id}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            title={source.title ?? source.url}
            className="text-xs text-primary hover:underline"
          >
            [{id}]
          </a>
        );
      })}
    </span>
  );
}

function ClaimList({ claims, sourcesById }: { claims: BriefClaim[]; sourcesById: Map<string, BriefSource> }) {
  if (claims.length === 0) {
    return <p className="text-sm text-muted-foreground">No data for this section.</p>;
  }
  return (
    <ul className="space-y-2">
      {claims.map((claim, i) => (
        <li key={i} className="text-sm">
          <span>{claim.text}</span>
          <SourceRefs ids={claim.source_ids} sourcesById={sourcesById} />
          <span className="ml-2 inline-flex gap-1 align-middle">
            <Badge variant={confidenceVariant(claim.confidence)}>{claim.confidence}</Badge>
            {claim.is_inference && <Badge variant="outline">inference</Badge>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function HookList({ hooks, sourcesById }: { hooks: BriefHook[]; sourcesById: Map<string, BriefSource> }) {
  if (hooks.length === 0) {
    return <p className="text-sm text-muted-foreground">No personalisation hooks generated.</p>;
  }
  return (
    <ul className="space-y-2">
      {hooks.map((hook, i) => (
        <li key={i} className="text-sm">
          <span>{hook.text}</span>
          <SourceRefs ids={hook.source_ids} sourcesById={sourcesById} />
          <Badge variant={confidenceVariant(hook.confidence)} className="ml-2 align-middle">
            {hook.confidence}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

export function BriefView({ brief }: { brief: ProspectBrief }) {
  const sourcesById = new Map(brief.sources.map((s) => [s.id, s]));
  const metadata = brief._synthesis_metadata;
  const isRuleBased = metadata?.synthesis_method === "rule_based";

  return (
    <div className="space-y-4">
      {isRuleBased ? (
        <Alert>
          <AlertDescription>
            This brief was synthesised without an AI provider available (no
            key configured, or the AI call failed), so it only contains what
            was directly supplied — no fabricated claims. See the sources
            list for exactly what backs each claim.
          </AlertDescription>
        </Alert>
      ) : metadata ? (
        <Alert>
          <AlertDescription>
            Synthesised with {metadata.provider ?? "AI"}
            {metadata.model ? ` (${metadata.model})` : ""} from {brief.sources.length}{" "}
            source{brief.sources.length === 1 ? "" : "s"}. Every claim below cites the
            source(s) it was drawn from, or is marked as an inference.
          </AlertDescription>
        </Alert>
      ) : null}

      {SECTIONS.map(({ key, label }) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle className="text-base">{label}</CardTitle>
          </CardHeader>
          <CardContent>
            <ClaimList claims={brief[key] as BriefClaim[]} sourcesById={sourcesById} />
          </CardContent>
        </Card>
      ))}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personalisation Hooks</CardTitle>
        </CardHeader>
        <CardContent>
          <HookList hooks={brief.hooks} sourcesById={sourcesById} />
        </CardContent>
      </Card>

      {brief.dos_and_donts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Do&apos;s and Don&apos;ts</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {brief.dos_and_donts.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sources ({brief.sources.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          {brief.sources.length === 0 ? (
            <p className="text-muted-foreground">
              No web sources — this brief was built from directly supplied
              information only.
            </p>
          ) : (
            brief.sources.map((s) => (
              <div key={s.id}>
                <span className="text-muted-foreground">[{s.id}]</span>{" "}
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary hover:underline"
                >
                  {s.title ?? s.url}
                </a>
              </div>
            ))
          )}
        </CardContent>
      </Card>
      <Separator />
    </div>
  );
}
