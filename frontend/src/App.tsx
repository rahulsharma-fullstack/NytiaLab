import { useCallback, useEffect, useState } from "react";
import "./App.css";
import {
  ApiError,
  getProfile,
  getRecommendations,
  getTenants,
  type OrgRecommendation,
  type OrgRecommendationResponse,
  type Tenant,
  type TenantProfile,
} from "./api";
import ContactPage from "./components/ContactPage";
import Controls from "./components/Controls";
import RecommendationList from "./components/RecommendationList";
import WorkforceSummary from "./components/WorkforceSummary";

type View = "dashboard" | "contact";

const DEFAULT_TOP_N = 10;

export default function App() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [topN, setTopN] = useState<number>(DEFAULT_TOP_N);
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [recommendations, setRecommendations] = useState<OrgRecommendationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Contact-flow state. View switches between the dashboard and the
  // ContactPage. Selected product is the one whose "Contact provider"
  // button was clicked. Going back to dashboard keeps every other state
  // untouched, so the user does not lose their tenant + recommendations.
  const [view, setView] = useState<View>("dashboard");
  const [selectedProduct, setSelectedProduct] = useState<OrgRecommendation | null>(null);

  const clampedTopN = Math.max(1, Math.min(50, Math.round(topN)));

  // ---- data loaders ----

  const loadTenantData = useCallback(async (tenantId: string, n: number) => {
    setLoading(true);
    setError(null);
    try {
      const [p, r] = await Promise.all([getProfile(tenantId), getRecommendations(tenantId, n)]);
      setProfile(p);
      setRecommendations(r);
    } catch (e) {
      const msg =
        e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Unknown error";
      setError(`Failed to load tenant data: ${msg}`);
      setProfile(null);
      setRecommendations(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const reloadRecommendations = useCallback(
    async (tenantId: string, n: number) => {
      setLoading(true);
      setError(null);
      try {
        const r = await getRecommendations(tenantId, n);
        setRecommendations(r);
      } catch (e) {
        const msg =
          e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Unknown error";
        setError(`Failed to refresh recommendations: ${msg}`);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // ---- initial load: tenants, then first tenant's data ----

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await getTenants();
        if (cancelled) return;
        setTenants(list);
        if (list.length > 0) {
          const firstId = list[0].id;
          setSelectedTenantId(firstId);
          // Kick off the dependent load without awaiting; loadTenantData
          // owns its own loading state.
          void loadTenantData(firstId, clampedTopN);
        } else {
          setLoading(false);
        }
      } catch (e) {
        if (cancelled) return;
        const msg =
          e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Unknown error";
        setError(`Could not load tenants: ${msg}`);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Mount-only loader; deps deliberately omitted so it does not re-run
    // when topN changes (a separate effect handles that).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- event handlers ----

  const handleTenantChange = (tenantId: string) => {
    setSelectedTenantId(tenantId);
    void loadTenantData(tenantId, clampedTopN);
  };

  const handleTopNChange = (next: number) => {
    setTopN(next);
    const c = Math.max(1, Math.min(50, Math.round(next)));
    if (selectedTenantId) {
      void reloadRecommendations(selectedTenantId, c);
    }
  };

  const handleRefresh = () => {
    if (selectedTenantId) {
      void reloadRecommendations(selectedTenantId, clampedTopN);
    }
  };

  const handleContactProvider = (product: OrgRecommendation) => {
    setSelectedProduct(product);
    setView("contact");
  };

  const handleBackToDashboard = () => {
    setView("dashboard");
    // Intentionally leave selectedProduct untouched so a quick re-open of
    // the contact page would reuse the same context. It is overwritten
    // on the next "Contact provider" click anyway.
  };

  // ---- render ----

  if (view === "contact" && selectedProduct && profile) {
    return (
      <div className="app">
        <header className="app-header">
          <div className="app-header-titles">
            <h1>Nytia Org Wellness Recommender</h1>
            <p className="app-tagline">
              Workforce-wide bulk recommendations for partner organisations
            </p>
          </div>
          <div className="app-header-meta">
            <span className="app-pill">Organization Dashboard</span>
          </div>
        </header>

        <main className="app-main">
          <ContactPage
            product={selectedProduct}
            tenantName={profile.tenant_name}
            totalEmployees={profile.total_employees}
            onBack={handleBackToDashboard}
          />
        </main>

        <footer className="app-footer">
          <a href="/demo">Per-employee demo</a>
          <span className="footer-dot">&middot;</span>
          <a href="/demo/org">Vanilla org demo</a>
          <span className="footer-dot">&middot;</span>
          <a href="/docs">API docs</a>
        </footer>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-titles">
          <h1>Nytia Org Wellness Recommender</h1>
          <p className="app-tagline">
            Workforce-wide bulk recommendations for partner organisations
          </p>
        </div>
        <div className="app-header-meta">
          <span className="app-pill">Organization Dashboard</span>
          <a className="switch-link" href="/demo">
            switch to per-employee &rarr;
          </a>
        </div>
      </header>

      <main className="app-main">
        <Controls
          tenants={tenants}
          selectedTenantId={selectedTenantId}
          topN={topN}
          onTenantChange={handleTenantChange}
          onTopNChange={handleTopNChange}
          onRefresh={handleRefresh}
          loading={loading}
        />

        {error && (
          <div role="alert" className="error-banner">
            {error}
          </div>
        )}

        <div className="grid">
          <WorkforceSummary profile={profile} loading={loading} />
          <RecommendationList
            data={recommendations}
            loading={loading}
            onContactProvider={handleContactProvider}
          />
        </div>
      </main>

      <footer className="app-footer">
        <a href="/demo">Per-employee demo</a>
        <span className="footer-dot">&middot;</span>
        <a href="/demo/org">Vanilla org demo</a>
        <span className="footer-dot">&middot;</span>
        <a href="/docs">API docs</a>
        <span className="footer-dot">&middot;</span>
        <a href="/health">Health</a>
      </footer>
    </div>
  );
}
