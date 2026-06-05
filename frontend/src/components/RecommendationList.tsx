import type { OrgRecommendationResponse } from "../api";
import RecommendationCard from "./RecommendationCard";

type Props = {
  data: OrgRecommendationResponse | null;
  loading: boolean;
};

function formatGenerated(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return "";
  }
}

export default function RecommendationList({ data, loading }: Props) {
  const headerMeta =
    data == null
      ? "-"
      : `${data.recommendations.length} item${data.recommendations.length === 1 ? "" : "s"}  |  generated ${formatGenerated(data.generated_at)}  |  ${data.algorithm_version}`;

  return (
    <section className="card">
      <header className="card-header">
        <span>Top recommended products</span>
        <span className="card-header-meta">{headerMeta}</span>
      </header>
      <div className="card-body">
        {loading && !data ? (
          <div className="loading">Loading recommendations...</div>
        ) : !data ? (
          <div className="empty">Pick a tenant to see ranked bulk recommendations.</div>
        ) : data.recommendations.length === 0 ? (
          <div className="empty">
            No products matched this workforce. The tenant has no health records yet, or the
            catalogue does not cover the workforce's needs.
          </div>
        ) : (
          <div className="rec-list">
            {data.recommendations.map((rec, i) => (
              <RecommendationCard key={rec.product_id} rec={rec} rank={i + 1} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
