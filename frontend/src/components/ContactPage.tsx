import { useState } from "react";
import type { OrgRecommendation } from "../api";

type Props = {
  product: OrgRecommendation;
  tenantName: string;
  totalEmployees: number;
  onBack: () => void;
};

function formatPrice(price: string | number | null, currency: string): string | null {
  if (price == null) return null;
  const n = typeof price === "number" ? price : Number(price);
  if (!Number.isFinite(n)) return null;
  return `${currency || "USD"} ${n.toFixed(2)}`;
}

export default function ContactPage({ product, tenantName, totalEmployees, onBack }: Props) {
  const [quantity, setQuantity] = useState<number>(totalEmployees);
  const [email, setEmail] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [sent, setSent] = useState<boolean>(false);

  const priceLabel = formatPrice(product.price, product.currency);
  const isTreatment = product.service_type === "condition_service";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Intentionally client-side only. There is no backend endpoint for
    // provider outreach yet; the spec marks this as a placeholder flow.
    setSent(true);
  };

  return (
    <div className="contact-page">
      <div className="contact-back-row">
        <button type="button" className="link-back" onClick={onBack}>
          &larr; Back to dashboard
        </button>
      </div>

      <section className="card contact-card">
        <header className="card-header">
          <span>Request bulk quote</span>
          <span className="badge badge-warn">Placeholder</span>
        </header>
        <div className="card-body">
          <div className="contact-context">
            <div className="contact-product">
              <div className="contact-product-label">Product</div>
              <div className="contact-product-name">{product.product_name}</div>
              <div className="contact-product-meta">
                <span className={`badge ${isTreatment ? "badge-treatment" : "badge-preventive"}`}>
                  {isTreatment ? "Treatment" : "Preventive"}
                </span>
                <span className="contact-meta-dot">&middot;</span>
                <span className="contact-product-category">{product.category}</span>
                {priceLabel && (
                  <>
                    <span className="contact-meta-dot">&middot;</span>
                    <span className="contact-product-price">{priceLabel} per seat</span>
                  </>
                )}
              </div>
            </div>
            <div className="contact-tenant">
              <div className="contact-tenant-label">For</div>
              <div className="contact-tenant-name">{tenantName}</div>
              <div className="contact-tenant-count">
                {totalEmployees} employee{totalEmployees === 1 ? "" : "s"}
              </div>
            </div>
          </div>

          <div className="contact-placeholder-note">
            Placeholder. Provider outreach workflow is not yet connected.
          </div>

          {sent ? (
            <div className="contact-success">
              <div className="contact-success-title">Request received</div>
              <div className="contact-success-body">
                Nytia will reach out to the provider on your behalf. You will
                hear back at <strong>{email || "your work email"}</strong>{" "}
                within two business days.
              </div>
              <div className="contact-success-actions">
                <button type="button" className="btn-primary" onClick={onBack}>
                  Back to dashboard
                </button>
              </div>
            </div>
          ) : (
            <form className="contact-form" onSubmit={handleSubmit}>
              <div className="form-row">
                <label htmlFor="contact-quantity">Quantity (seats)</label>
                <input
                  id="contact-quantity"
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    if (Number.isFinite(v)) setQuantity(v);
                  }}
                />
                <div className="form-hint">
                  Defaults to your workforce size ({totalEmployees}).
                </div>
              </div>

              <div className="form-row">
                <label htmlFor="contact-email">Work email</label>
                <input
                  id="contact-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@yourcompany.com"
                  required
                />
              </div>

              <div className="form-row">
                <label htmlFor="contact-notes">Notes for the provider</label>
                <textarea
                  id="contact-notes"
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Anything they should know before they reach out..."
                />
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  Send request
                </button>
                <button type="button" className="link-back" onClick={onBack}>
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
