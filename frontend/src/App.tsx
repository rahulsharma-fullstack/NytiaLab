import "./App.css";

// Phase 1 placeholder. The real org dashboard is built in Phase 2.
// Source of truth for the React org dashboard. The /demo and /demo/org
// vanilla pages stay as-is alongside this app.
export default function App() {
  return (
    <main className="placeholder">
      <header className="placeholder-header">
        <h1>Nytia Org Dashboard</h1>
        <span className="placeholder-pill">React build</span>
      </header>
      <p className="placeholder-lead">
        Coming together. This page is the new home for the org-level workforce
        dashboard, rebuilt in React + TypeScript.
      </p>
      <p className="placeholder-note">
        Phase 1 scaffold. The real dashboard, tenant data, and the Contact
        Provider flow land in the next phases.
      </p>
      <ul className="placeholder-links">
        <li>
          <a href="/demo">Existing per-employee demo</a>
        </li>
        <li>
          <a href="/demo/org">Existing org-level demo (vanilla JS)</a>
        </li>
        <li>
          <a href="/docs">API docs (Swagger)</a>
        </li>
      </ul>
    </main>
  );
}
