import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type {
  ActivityItem,
  ActivityType,
  BriefClaim,
  BriefSource,
  CareerEntry,
  PersonalizationHook,
  ProspectBrief,
} from "@/lib/api";

const CLAIM_SECTIONS: { key: keyof ProspectBrief; label: string }[] = [
  { key: "snapshot", label: "Executive Snapshot" },
  { key: "current_role", label: "Current Role" },
  { key: "company_overview", label: "Company Overview" },
];

const CLAIM_SECTIONS_2: { key: keyof ProspectBrief; label: string }[] = [
  { key: "expertise", label: "Expertise" },
];

const CLAIM_SECTIONS_3: { key: keyof ProspectBrief; label: string }[] = [
  { key: "recurring_themes", label: "Recurring Themes" },
  { key: "company_context", label: "Company & Industry Context" },
];

const ACTIVITY_TYPE_LABELS: Record<ActivityType, string> = {
  original_post: "Original Posts",
  repost_or_share: "Reposts & Shares",
  comment: "Comments",
  article_or_publication: "Articles & Publications",
  interview_or_podcast: "Interviews & Podcasts",
  talk_or_presentation: "Talks & Presentations",
  professional_announcement: "Professional Announcements",
  other_public_activity: "Other Public Activity",
};

const ACTIVITY_TYPE_ORDER: ActivityType[] = [
  "original_post",
  "repost_or_share",
  "comment",
  "article_or_publication",
  "interview_or_podcast",
  "talk_or_presentation",
  "professional_announcement",
  "other_public_activity",
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
          {claim.date && <span className="ml-1 text-xs text-muted-foreground">({claim.date})</span>}
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

function CareerTimelineList({
  entries,
  sourcesById,
}: {
  entries: CareerEntry[];
  sourcesById: Map<string, BriefSource>;
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">No career history available.</p>;
  }
  return (
    <ul className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="text-sm">
          <div className="font-medium">
            {entry.title} · {entry.organization}
          </div>
          <div className="text-xs text-muted-foreground">
            {entry.start_date ?? "?"} – {entry.end_date ?? "present"}
          </div>
          {entry.description && <p className="mt-1">{entry.description}</p>}
          <span className="inline-flex items-center gap-1">
            <SourceRefs ids={entry.source_ids} sourcesById={sourcesById} />
            <Badge variant={confidenceVariant(entry.confidence)}>{entry.confidence}</Badge>
          </span>
        </li>
      ))}
    </ul>
  );
}

function ActivityList({ items, sourcesById }: { items: ActivityItem[]; sourcesById: Map<string, BriefSource> }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No public activity found.</p>;
  }
  const grouped = new Map<ActivityType, ActivityItem[]>();
  for (const item of items) {
    const list = grouped.get(item.activity_type) ?? [];
    list.push(item);
    grouped.set(item.activity_type, list);
  }
  return (
    <div className="space-y-4">
      {ACTIVITY_TYPE_ORDER.filter((type) => grouped.has(type)).map((type) => (
        <div key={type}>
          <h4 className="mb-1 text-sm font-medium">{ACTIVITY_TYPE_LABELS[type]}</h4>
          <ul className="space-y-2">
            {grouped.get(type)!.map((item, i) => (
              <li key={i} className="text-sm">
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                    {item.topic}
                  </a>
                ) : (
                  <span>{item.topic}</span>
                )}
                {item.published_at && (
                  <span className="ml-1 text-xs text-muted-foreground">({item.published_at})</span>
                )}
                <p className="text-muted-foreground">{item.summary}</p>
                {item.relevance && <p className="text-xs italic text-muted-foreground">{item.relevance}</p>}
                <span className="inline-flex items-center gap-1">
                  <SourceRefs ids={item.source_ids} sourcesById={sourcesById} />
                  <Badge variant={confidenceVariant(item.confidence)}>{item.confidence}</Badge>
                  {!item.authored_by_person && <Badge variant="outline">not authored by person</Badge>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function PersonalizationHookList({
  hooks,
  sourcesById,
}: {
  hooks: PersonalizationHook[];
  sourcesById: Map<string, BriefSource>;
}) {
  if (hooks.length === 0) {
    return <p className="text-sm text-muted-foreground">No personalisation hooks generated.</p>;
  }
  return (
    <ul className="space-y-3">
      {hooks.map((hook, i) => (
        <li key={i} className="text-sm">
          <p>
            <span className="font-medium">Evidence: </span>
            {hook.evidence}
          </p>
          <p>
            <span className="font-medium">Relevance: </span>
            {hook.relevance}
          </p>
          <p>
            <span className="font-medium">Outreach angle: </span>
            {hook.outreach_angle}
          </p>
          <span className="inline-flex items-center gap-1">
            <SourceRefs ids={hook.source_ids} sourcesById={sourcesById} />
            <Badge variant={confidenceVariant(hook.confidence)}>{hook.confidence}</Badge>
          </span>
        </li>
      ))}
    </ul>
  );
}

function OutreachStrategyCard({ strategy }: { strategy: ProspectBrief["outreach_strategy"] }) {
  return (
    <div className="space-y-2 text-sm">
      {strategy.angle && (
        <p>
          <span className="font-medium">Angle: </span>
          {strategy.angle}
        </p>
      )}
      {strategy.primary_hooks.length > 0 && (
        <div>
          <span className="font-medium">Primary hooks:</span>
          <ul className="list-disc space-y-1 pl-5">
            {strategy.primary_hooks.map((hook, i) => (
              <li key={i}>{hook}</li>
            ))}
          </ul>
        </div>
      )}
      {strategy.question_or_value_prop && (
        <p>
          <span className="font-medium">Question / value prop: </span>
          {strategy.question_or_value_prop}
        </p>
      )}
      {strategy.opening_approach && (
        <p>
          <span className="font-medium">Opening approach: </span>
          {strategy.opening_approach}
        </p>
      )}
      {strategy.avoid.length > 0 && (
        <div>
          <span className="font-medium">Avoid:</span>
          <ul className="list-disc space-y-1 pl-5">
            {strategy.avoid.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {!strategy.angle &&
        strategy.primary_hooks.length === 0 &&
        !strategy.question_or_value_prop &&
        !strategy.opening_approach &&
        strategy.avoid.length === 0 && (
          <p className="text-muted-foreground">No outreach strategy generated.</p>
        )}
    </div>
  );
}

function ResearchGapsCard({ gaps }: { gaps: ProspectBrief["research_gaps"] }) {
  const sections: { key: keyof ProspectBrief["research_gaps"]; label: string }[] = [
    { key: "missing_information", label: "Missing Information" },
    { key: "limited_coverage_areas", label: "Limited Coverage Areas" },
    { key: "conflicting_information", label: "Conflicting Information" },
    { key: "unverified_claims", label: "Unverified Claims" },
    { key: "inaccessible_sources", label: "Inaccessible Sources" },
  ];
  const visible = sections.filter((s) => gaps[s.key].length > 0);
  if (visible.length === 0) {
    return <p className="text-sm text-muted-foreground">No research gaps noted.</p>;
  }
  return (
    <div className="space-y-3 text-sm">
      {visible.map((s) => (
        <div key={s.key}>
          <h4 className="mb-1 font-medium">{s.label}</h4>
          <ul className="list-disc space-y-1 pl-5">
            {gaps[s.key].map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function sourceTypeLabel(type: BriefSource["source_type"]): string {
  return type.replace(/_/g, " ");
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
            Research collected; AI synthesis unavailable. This brief was
            synthesised without an AI provider available (no key
            configured, or the AI call failed), so it only contains what
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

      {CLAIM_SECTIONS.map(({ key, label }) => (
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
          <CardTitle className="text-base">Career Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <CareerTimelineList entries={brief.career_timeline} sourcesById={sourcesById} />
        </CardContent>
      </Card>

      {CLAIM_SECTIONS_2.map(({ key, label }) => (
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
          <CardTitle className="text-base">Public Content & Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <ActivityList items={brief.activity} sourcesById={sourcesById} />
        </CardContent>
      </Card>

      {CLAIM_SECTIONS_3.map(({ key, label }) => (
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
          <CardTitle className="text-base">Communication Style</CardTitle>
        </CardHeader>
        <CardContent>
          <ClaimList claims={brief.communication_style} sourcesById={sourcesById} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Likely Priorities</CardTitle>
        </CardHeader>
        <CardContent>
          <ClaimList claims={brief.likely_priorities} sourcesById={sourcesById} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personalization Opportunities</CardTitle>
        </CardHeader>
        <CardContent>
          <PersonalizationHookList hooks={brief.personalization_hooks} sourcesById={sourcesById} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Suggested Outreach Strategy</CardTitle>
        </CardHeader>
        <CardContent>
          <OutreachStrategyCard strategy={brief.outreach_strategy} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Source Register ({brief.sources.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
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
                <span className="ml-2 inline-flex gap-1 align-middle">
                  <Badge variant="outline">{sourceTypeLabel(s.source_type)}</Badge>
                  {s.publisher && <Badge variant="secondary">{s.publisher}</Badge>}
                  <Badge variant={confidenceVariant(s.confidence)}>{s.confidence}</Badge>
                </span>
                {s.published_at && (
                  <span className="ml-1 text-xs text-muted-foreground">
                    published {s.published_at}
                  </span>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Research Gaps & Confidence</CardTitle>
        </CardHeader>
        <CardContent>
          <ResearchGapsCard gaps={brief.research_gaps} />
        </CardContent>
      </Card>

      <Separator />
    </div>
  );
}
