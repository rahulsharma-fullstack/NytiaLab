import type { OrgRecommendation } from "../api";

type Props = {
  rec: OrgRecommendation;
  rank: number; // 1-based
  onContactProvider: (product: OrgRecommendation) => void;
};

function formatPrice(price: string | number | null, currency: string): string | null {
  if (price == null) return null;
  const n = typeof price === "number" ? price : Number(price);
  if (!Number.isFinite(n)) return null;
  return `${currency || "USD"} ${n.toFixed(2)}`;
}

export default function RecommendationCard({ rec, rank, onContactProvider }: Props) {
  const isTreatment = rec.service_type === "condition_service";
  const priceLabel = formatPrice(rec.price, rec.currency);
  return (
    <article className={`rec-card${rank === 1 ? " rec-card-top" : ""}`}>
      <div className="rec-head">
        <div className="rec-title-block">
          <span className={`rec-rank${rank === 1 ? " rec-rank-top" : ""}`}>{rank}</span>
          <div>
            <h3 className="rec-name">{rec.product_name}</h3>
            <div className="rec-meta">
              <span className={`badge ${isTreatment ? "badge-treatment" : "badge-preventive"}`}>
                {isTreatment ? "Treatment" : "Preventive"}
              </span>
              <span className="rec-meta-dot">&middot;</span>
              <span className="rec-category">{rec.category}</span>
              {priceLabel && (
                <>
                  <span className="rec-meta-dot">&middot;</span>
                  <span className="rec-price">{priceLabel}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="rec-score" title="Org-level recommendation score (higher = better fit)">
          <span className="rec-score-value">{rec.score.toFixed(1)}</span>
          <span className="rec-score-label">score</span>
        </div>
      </div>

      <ul className="rec-reasons">
        {rec.reasons.map((reason, i) => (
          <li key={i}>{reason}</li>
        ))}
      </ul>

      <div className="rec-actions">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => onContactProvider(rec)}
          aria-label={`Contact provider for ${rec.product_name}`}
        >
          Contact provider
        </button>
      </div>
    </article>
  );
}
