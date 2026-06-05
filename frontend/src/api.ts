// Typed client for the Nytia FastAPI backend.
//
// The React app is served by FastAPI at /dashboard/, so it is same-origin
// with the API. All paths are relative. No base URL configuration needed.

// ---------- Types matching the backend response shapes ----------

export type Tenant = {
  id: string;
  name: string;
  created_at: string;
};

export type DimensionPressure = {
  name: string;
  suffering_count: number;
  at_risk_count: number;
  total_affected: number;
  percent_affected: number;
  pressure_score: number;
};

export type TenantProfile = {
  tenant_id: string;
  tenant_name: string;
  total_employees: number;
  conditions: DimensionPressure[];
  factors: DimensionPressure[];
};

export type OrgRecommendation = {
  product_id: number;
  product_name: string;
  category: string;
  service_type: "factor_service" | "condition_service";
  price: string | number | null;
  currency: string;
  score: number;
  reasons: string[];
};

export type OrgRecommendationResponse = {
  tenant_id: string;
  tenant_name: string;
  total_employees: number;
  algorithm_version: string;
  generated_at: string;
  recommendations: OrgRecommendation[];
};

// ---------- Error type ----------

export class ApiError extends Error {
  status: number;
  errorCode: string | undefined;

  constructor(status: number, errorCode: string | undefined, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

// ---------- Internal fetch helper ----------

async function fetchJson<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path);
  } catch (e) {
    throw new ApiError(0, "network_error", e instanceof Error ? e.message : "Network error");
  }
  if (!res.ok) {
    let detail = res.statusText;
    let errorCode: string | undefined;
    try {
      const body = await res.json();
      if (body && typeof body === "object") {
        errorCode = typeof body.error === "string" ? body.error : undefined;
        if (typeof body.detail === "string") {
          detail = body.detail;
        } else if (Array.isArray(body.detail)) {
          detail = body.detail
            .map((d: { msg?: string }) => d?.msg)
            .filter(Boolean)
            .join("; ");
        }
      }
    } catch {
      // body was not JSON; keep statusText.
    }
    throw new ApiError(res.status, errorCode, detail || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

// ---------- Public API ----------

export function getTenants(): Promise<Tenant[]> {
  return fetchJson<Tenant[]>("/tenants");
}

export function getProfile(tenantId: string): Promise<TenantProfile> {
  return fetchJson<TenantProfile>(`/tenants/${encodeURIComponent(tenantId)}/profile`);
}

export function getRecommendations(
  tenantId: string,
  topN: number,
): Promise<OrgRecommendationResponse> {
  return fetchJson<OrgRecommendationResponse>(
    `/tenants/${encodeURIComponent(tenantId)}/recommendations?top_n=${topN}`,
  );
}
