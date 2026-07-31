import { RecommendationCard } from "@/components/diagnostics/RecommendationCard";
import type { DiagnosticRecommendation, RecommendationPriority } from "@/data/diagnostic-recommendations";

const priorityWeight: Record<RecommendationPriority, number> = {
  CRITICAL: 3,
  HIGH: 2,
  MEDIUM: 1,
};

export function sortRecommendations(recommendations: DiagnosticRecommendation[]): DiagnosticRecommendation[] {
  return [...recommendations].sort((left, right) =>
    priorityWeight[right.priority] - priorityWeight[left.priority]
    || right.expectedImpact - left.expectedImpact
    || right.confidence - left.confidence
    || left.title.localeCompare(right.title),
  );
}

export function PrioritizedRecommendations({ recommendations, onToggleApplied }: { recommendations: DiagnosticRecommendation[]; onToggleApplied?: (id: string) => void }) {
  if (recommendations.length === 0) {
    return <div className="rounded-xl border border-dashed bg-card p-10 text-center text-sm text-muted-foreground">No recommendations yet. Complete loss-pattern analysis to generate evidence-based actions.</div>;
  }

  return <div className="space-y-3">
    {sortRecommendations(recommendations).map((recommendation, index) => <RecommendationCard key={recommendation.id} recommendation={recommendation} rank={index + 1} onToggleApplied={onToggleApplied} />)}
  </div>;
}