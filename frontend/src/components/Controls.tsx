import type { Tenant } from "../api";

type Props = {
  tenants: Tenant[];
  selectedTenantId: string | null;
  topN: number;
  onTenantChange: (tenantId: string) => void;
  onTopNChange: (topN: number) => void;
  onRefresh: () => void;
  loading: boolean;
};

export default function Controls({
  tenants,
  selectedTenantId,
  topN,
  onTenantChange,
  onTopNChange,
  onRefresh,
  loading,
}: Props) {
  return (
    <div className="controls">
      <div className="control-field">
        <label htmlFor="tenant-select">Tenant</label>
        <select
          id="tenant-select"
          value={selectedTenantId ?? ""}
          onChange={(e) => onTenantChange(e.target.value)}
          disabled={tenants.length === 0}
        >
          {tenants.length === 0 ? (
            <option value="">Loading tenants...</option>
          ) : (
            tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.id})
              </option>
            ))
          )}
        </select>
      </div>

      <div className="control-field">
        <label htmlFor="top-n">Top results</label>
        <input
          id="top-n"
          type="number"
          min={1}
          max={50}
          value={topN}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (Number.isFinite(v)) onTopNChange(v);
          }}
        />
      </div>

      <button
        type="button"
        className="btn-primary"
        onClick={onRefresh}
        disabled={loading || !selectedTenantId}
      >
        {loading ? "Refreshing..." : "Refresh"}
      </button>

      <span className="algo-label" title="Algorithm version used to score recommendations">
        algorithm: org-rules-v1
      </span>
    </div>
  );
}
