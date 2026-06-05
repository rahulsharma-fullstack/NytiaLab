import type { DimensionPressure, TenantProfile } from "../api";

type Props = {
  profile: TenantProfile | null;
  loading: boolean;
};

const TOP_N_ROWS = 5;

function DimensionTable({ rows, title }: { rows: DimensionPressure[]; title: string }) {
  if (rows.length === 0) {
    return (
      <div className="dim-block">
        <h3 className="dim-title">{title}</h3>
        <div className="empty">No entries.</div>
      </div>
    );
  }
  const top = rows.slice(0, TOP_N_ROWS);
  return (
    <div className="dim-block">
      <h3 className="dim-title">{title}</h3>
      <table className="dim-table">
        <thead>
          <tr>
            <th>Name</th>
            <th className="num">Suffer</th>
            <th className="num">At risk</th>
            <th className="pct-col">% affected</th>
            <th className="num">Pressure</th>
          </tr>
        </thead>
        <tbody>
          {top.map((d) => (
            <tr key={d.name}>
              <td className="name-cell">{d.name}</td>
              <td className="num">{d.suffering_count}</td>
              <td className="num">{d.at_risk_count}</td>
              <td className="pct-col">
                <div className="pct-row">
                  <div className="pct-bar-track" aria-hidden="true">
                    <div
                      className="pct-bar-fill"
                      style={{ width: `${Math.min(100, d.percent_affected)}%` }}
                    />
                  </div>
                  <span className="pct-value">{d.percent_affected.toFixed(1)}%</span>
                </div>
              </td>
              <td className="num">{d.pressure_score.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > TOP_N_ROWS && (
        <div className="dim-footer">
          showing top {TOP_N_ROWS} of {rows.length}
        </div>
      )}
    </div>
  );
}

export default function WorkforceSummary({ profile, loading }: Props) {
  if (loading && !profile) {
    return (
      <section className="card">
        <header className="card-header">Workforce health summary</header>
        <div className="card-body">
          <div className="loading">Loading workforce data...</div>
        </div>
      </section>
    );
  }
  if (!profile) {
    return (
      <section className="card">
        <header className="card-header">Workforce health summary</header>
        <div className="card-body">
          <div className="empty">Pick a tenant to load the workforce summary.</div>
        </div>
      </section>
    );
  }

  return (
    <section className="card">
      <header className="card-header">Workforce health summary</header>
      <div className="card-body">
        <div className="summary-head">
          <div className="summary-tenant">
            <div className="summary-tenant-name">{profile.tenant_name}</div>
            <div className="summary-tenant-id">{profile.tenant_id}</div>
          </div>
          <div className="summary-headcount">
            <div className="summary-headcount-value">{profile.total_employees}</div>
            <div className="summary-headcount-label">employees</div>
          </div>
        </div>

        <DimensionTable rows={profile.conditions} title="Top conditions (by pressure)" />
        <DimensionTable rows={profile.factors} title="Top factors (by pressure)" />
      </div>
    </section>
  );
}
