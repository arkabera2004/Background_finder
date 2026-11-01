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
  CompanyProfile,
  EducationEntry,
  PersonalizationHook,
  ProspectBrief,
  RelatedPersonality,
  SameNameMatch,
} from "@/lib/api";

const PUBLICATION_ACTIVITY_TYPES: ActivityType[] = [
  "article_or_publication",
  "interview_or_podcast",
  "talk_or_presentation",
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

function EmptySection({ text }: { text: string }) {
  return <p className="text-sm text-muted-foreground">{text}</p>;
}

function ClaimList({
  claims,
  sourcesById,
  emptyText = "No data for this section.",
}: {
  claims: BriefClaim[];
  sourcesById: Map<string, BriefSource>;
  emptyText?: string;
}) {
  if (claims.length === 0) {
    return <EmptySection text={emptyText} />;
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

function IdentityVerificationCard({ identity }: { identity: ProspectBrief["identity_verification"] }) {
  if (!identity) {
    return <EmptySection text="No identity verification data available." />;
  }
  return (
    <div className="space-y-2 text-sm">
      {identity.profile_url && (
        <p>
          <span className="font-medium">Profile used: </span>
          <a href={identity.profile_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
            {identity.profile_url}
          </a>
        </p>
      )}
      {identity.matched_identifiers.length > 0 && (
        <div>
          <span className="font-medium">Matching identifiers:</span>
          <ul className="list-disc space-y-1 pl-5">
            {identity.matched_identifiers.map((id, i) => (
              <li key={i}>{id}</li>
            ))}
          </ul>
        </div>
      )}
      <p>
        <span className="font-medium">Confidence: </span>
        <Badge variant={confidenceVariant(identity.confidence)}>{identity.confidence}</Badge>
      </p>
      {identity.limitations && (
        <p className="text-xs italic text-muted-foreground">{identity.limitations}</p>
      )}
    </div>
  );
}

function EducationList({
  entries,
  sourcesById,
}: {
  entries: EducationEntry[];
  sourcesById: Map<string, BriefSource>;
}) {
  if (entries.length === 0) {
    return <EmptySection text="No publicly documented education history was found." />;
  }
  return (
    <ul className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="text-sm">
          <div className="font-medium">
            {entry.degree ? `${entry.degree} ` : ""}
            {entry.field ? `in ${entry.field} ` : ""}at {entry.institution}
          </div>
          <div className="text-xs text-muted-foreground">
            {entry.start_date ?? "?"} – {entry.end_date ?? "?"} (dates {entry.date_precision})
          </div>
          <span className="inline-flex items-center gap-1">
            <SourceRefs ids={entry.source_ids} sourcesById={sourcesById} />
            <Badge variant={confidenceVariant(entry.confidence)}>{entry.confidence}</Badge>
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
    return <EmptySection text="No career history available." />;
  }
  return (
    <ul className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="text-sm">
          <div className="font-medium">
            {entry.title} · {entry.organization}
          </div>
          <div className="text-xs text-muted-foreground">
            {entry.start_date ?? "?"} – {entry.end_date ?? "present"} (dates {entry.date_precision})
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

function CompanyProfileList({
  entries,
  sourcesById,
}: {
  entries: CompanyProfile[];
  sourcesById: Map<string, BriefSource>;
}) {
  if (entries.length === 0) {
    return <EmptySection text="No per-company detail available." />;
  }
  return (
    <div className="space-y-4">
      {entries.map((entry, i) => (
        <div key={i} className="text-sm">
          <div className="font-medium">{entry.name}</div>
          {entry.website && (
            <a href={entry.website} target="_blank" rel="noreferrer" className="text-primary hover:underline">
              {entry.website}
            </a>
          )}
          {entry.what_they_do && <p>{entry.what_they_do}</p>}
          <p className="text-muted-foreground">
            {entry.person_role} · {entry.start_date ?? "?"} – {entry.end_date ?? "present"} (dates{" "}
            {entry.date_precision})
          </p>
          {entry.role_scope && <p>{entry.role_scope}</p>}
          {entry.related_projects.length > 0 && (
            <ul className="list-disc space-y-1 pl-5">
              {entry.related_projects.map((p, j) => (
                <li key={j}>{p}</li>
              ))}
            </ul>
          )}
          {entry.uncertainty_note && (
            <p className="text-xs italic text-muted-foreground">{entry.uncertainty_note}</p>
          )}
          <span className="inline-flex items-center gap-1">
            <SourceRefs ids={entry.source_ids} sourcesById={sourcesById} />
            <Badge variant={confidenceVariant(entry.confidence)}>{entry.confidence}</Badge>
          </span>
        </div>
      ))}
    </div>
  );
}

function ActivityList({
  items,
  sourcesById,
  emptyText,
}: {
  items: ActivityItem[];
  sourcesById: Map<string, BriefSource>;
  emptyText: string;
}) {
  if (items.length === 0) {
    return <EmptySection text={emptyText} />;
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

function SameNameList({
  entries,
  sourcesById,
}: {
  entries: SameNameMatch[];
  sourcesById: Map<string, BriefSource>;
}) {
  if (entries.length === 0) {
    return <EmptySection text="No meaningful same-name matches were found." />;
  }
  return (
    <ul className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="text-sm">
          <div className="font-medium">{entry.name}</div>
          <p>{entry.identity_summary}</p>
          {entry.distinguishing_info && <p className="text-muted-foreground">{entry.distinguishing_info}</p>}
          <p className="text-xs italic text-muted-foreground">Why confusable: {entry.why_confusable}</p>
          <p className="text-xs italic text-muted-foreground">Why different: {entry.why_different}</p>
          <SourceRefs ids={entry.source_ids} sourcesById={sourcesById} />
        </li>
      ))}
    </ul>
  );
}

function RelatedPersonalityList({
  entries,
  sourcesById,
}: {
  entries: RelatedPersonality[];
  sourcesById: Map<string, BriefSource>;
}) {
  if (entries.length === 0) {
    return <EmptySection text="No demonstrably connected personalities were found." />;
  }
  return (
    <ul className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="text-sm">
          <div className="font-medium">
            {entry.name}
            {entry.role ? ` · ${entry.role}` : ""}
          </div>
          <p className="text-muted-foreground">{entry.connection_type}</p>
          <p>{entry.evidence}</p>
          <span className="inline-flex items-center gap-1">
            <SourceRefs ids={entry.source_ids} sourcesById={sourcesById} />
            <Badge variant={entry.strength === "confirmed" ? "default" : "outline"}>{entry.strength}</Badge>
          </span>
        </li>
      ))}
    </ul>
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
    return <EmptySection text="No conversation opportunities generated." />;
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
        strategy.avoid.length === 0 && <EmptySection text="No outreach strategy generated." />}
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
    return <EmptySection text="No research gaps noted." />;
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function BriefView({ brief }: { brief: ProspectBrief }) {
  const sourcesById = new Map(brief.sources.map((s) => [s.id, s]));
  const metadata = brief._synthesis_metadata;
  const isRuleBased = metadata?.synthesis_method === "rule_based";

  const posts = brief.activity.filter((a) => !PUBLICATION_ACTIVITY_TYPES.includes(a.activity_type));
  const publications = brief.activity.filter((a) => PUBLICATION_ACTIVITY_TYPES.includes(a.activity_type));

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

      {/* 1. Identity Verification */}
      <Section title="Identity Verification">
        <IdentityVerificationCard identity={brief.identity_verification} />
      </Section>

      {/* 2. Executive Overview */}
      <Section title="Executive Overview">
        <ClaimList claims={brief.snapshot} sourcesById={sourcesById} />
      </Section>

      {/* 3. Detailed Person Summary */}
      <Section title="Detailed Person Summary">
        <ClaimList claims={brief.detailed_summary} sourcesById={sourcesById} />
      </Section>

      {/* 4. Education & Early Background */}
      <Section title="Education & Early Background">
        <EducationList entries={brief.education} sourcesById={sourcesById} />
      </Section>

      {/* 5. Complete Career Timeline */}
      <Section title="Complete Career Timeline">
        <CareerTimelineList entries={brief.career_timeline} sourcesById={sourcesById} />
      </Section>

      {/* 6. Company-by-Company Overview */}
      <Section title="Company-by-Company Overview">
        <CompanyProfileList entries={brief.company_profiles} sourcesById={sourcesById} />
      </Section>

      {/* 7. Current Role & Responsibilities */}
      <Section title="Current Role & Responsibilities">
        <ClaimList claims={brief.current_role} sourcesById={sourcesById} />
      </Section>

      {/* 8. Achievements & Milestones */}
      <Section title="Achievements & Milestones">
        <ClaimList
          claims={brief.achievements}
          sourcesById={sourcesById}
          emptyText="No independently verifiable achievements were found."
        />
      </Section>

      {/* 9. Research, Expertise & Professional Interests */}
      <Section title="Research, Expertise & Professional Interests">
        <div className="space-y-4">
          <ClaimList claims={brief.expertise} sourcesById={sourcesById} />
          <ClaimList claims={brief.recurring_themes} sourcesById={sourcesById} />
        </div>
      </Section>

      <Section title="Company Context">
        <ClaimList claims={brief.company_context} sourcesById={sourcesById} />
      </Section>

      <Section title="Communication Style">
        <ClaimList claims={brief.communication_style} sourcesById={sourcesById} />
      </Section>

      <Section title="Likely Priorities">
        <ClaimList claims={brief.likely_priorities} sourcesById={sourcesById} />
      </Section>

      {/* 10. Posts, Reposts & Public Activity */}
      <Section title="Posts, Reposts & Public Activity">
        <ActivityList
          items={posts}
          sourcesById={sourcesById}
          emptyText="No public posts or reposts were accessible for this person."
        />
      </Section>

      {/* 11. Publications, Talks & Interviews */}
      <Section title="Publications, Talks & Interviews">
        <ActivityList
          items={publications}
          sourcesById={sourcesById}
          emptyText="No publications, talks, or interviews were found."
        />
      </Section>

      {/* 12. People with the Same Name */}
      <Section title="People with the Same Name">
        <SameNameList entries={brief.same_name_people} sourcesById={sourcesById} />
      </Section>

      {/* 13. Related Personalities */}
      <Section title="Related Personalities">
        <RelatedPersonalityList entries={brief.related_personalities} sourcesById={sourcesById} />
      </Section>

      {/* 14. Common Ground & Conversation Opportunities */}
      <Section title="Common Ground & Conversation Opportunities">
        <PersonalizationHookList hooks={brief.personalization_hooks} sourcesById={sourcesById} />
      </Section>

      {/* 15. Personalized Outreach Brief */}
      <Section title="Personalized Outreach Brief">
        <OutreachStrategyCard strategy={brief.outreach_strategy} />
      </Section>

      {/* 16. Sources & Evidence */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sources & Evidence ({brief.sources.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {brief.sources.length === 0 ? (
            <EmptySection text="No web sources — this brief was built from directly supplied information only." />
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

      {/* 17. Research Gaps, Conflicts & Limitations */}
      <Section title="Research Gaps, Conflicts & Limitations">
        <ResearchGapsCard gaps={brief.research_gaps} />
      </Section>

      <Separator />
    </div>
  );
}
