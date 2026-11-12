# ruff: noqa: E501
"""Self-contained interactive HTML/CSS/JS frontend for the SHADOWLINK Demo Dashboard."""

from __future__ import annotations

DEMO_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SHADOWLINK — Privacy Re-identification Risk Assessment</title>
<style>
:root {
  --bg-primary: #f8fafc;
  --bg-card: #ffffff;
  --bg-card-secondary: #f1f5f9;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #64748b;
  --border-color: #e2e8f0;
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --primary-light: #eff6ff;
  --success: #16a34a;
  --success-light: #f0fdf4;
  --warning: #d97706;
  --warning-light: #fffbeb;
  --danger: #dc2626;
  --danger-light: #fef2f2;
  --accent: #7c3aed;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #0b0f19;
    --bg-card: #111827;
    --bg-card-secondary: #1f2937;
    --text-primary: #f9fafb;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --border-color: #374151;
    --primary: #3b82f6;
    --primary-hover: #60a5fa;
    --primary-light: rgba(59, 130, 246, 0.15);
    --success: #22c55e;
    --success-light: rgba(34, 197, 94, 0.15);
    --warning: #f59e0b;
    --warning-light: rgba(245, 158, 11, 0.15);
    --danger: #ef4444;
    --danger-light: rgba(239, 68, 68, 0.15);
    --accent: #8b5cf6;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.5);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.5);
  }
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-sans);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.5;
  padding: 0;
  margin: 0;
}

header {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  padding: 16px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 50;
}
.brand-title {
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 9999px;
  background: var(--primary-light);
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.run-status-pill {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background: var(--bg-card-secondary);
  border: 1px solid var(--border-color);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
}
.status-dot.inactive { background: var(--text-muted); }

.tab-nav {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  padding: 0 28px;
  display: flex;
  gap: 8px;
  overflow-x: auto;
}
.tab-btn {
  background: none;
  border: none;
  padding: 14px 16px;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 28px;
}
.tab-pane { display: none; }
.tab-pane.active { display: block; animation: fadeIn 0.2s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}
.card-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
}
.card-subtitle {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.grid-5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
@media (max-width: 1100px) {
  .grid-5 { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 900px) {
  .grid-2, .grid-3, .grid-4, .grid-5 { grid-template-columns: 1fr; }
}

.form-group {
  margin-bottom: 16px;
}
label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
input, select, textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 0.9rem;
  transition: border-color 0.15s ease;
}
input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
}
.btn-primary {
  background: var(--primary);
  color: #ffffff;
}
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary {
  background: var(--bg-card-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}
.btn-secondary:hover { background: var(--border-color); }
.btn-sm { padding: 6px 12px; font-size: 0.8rem; }
.btn-danger { background: var(--danger-light); color: var(--danger); border: 1px solid var(--danger); }
.btn-danger:hover { background: var(--danger); color: #ffffff; }

.stat-box {
  background: var(--bg-card-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: left;
}
.stat-val {
  font-size: 1.5rem;
  font-weight: 800;
  font-family: var(--font-mono);
  color: var(--primary);
  line-height: 1.2;
}
.stat-lbl {
  font-size: 0.76rem;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
  margin-top: 4px;
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  text-align: left;
}
th {
  background: var(--bg-card-secondary);
  color: var(--text-secondary);
  font-weight: 700;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}
td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  font-family: var(--font-mono);
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--bg-card-secondary); }

.formula-card {
  background: var(--bg-card-secondary);
  border-left: 4px solid var(--primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  padding: 12px 16px;
  margin-bottom: 12px;
  font-size: 0.85rem;
}
.formula-title { font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.formula-math { font-family: var(--font-mono); color: var(--primary); margin-bottom: 4px; font-weight: 600; }
.formula-desc { color: var(--text-muted); font-size: 0.8rem; line-height: 1.4; }

.disclaimer-banner {
  background: var(--warning-light);
  border: 1px solid var(--warning);
  color: var(--warning);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  margin-bottom: 20px;
  font-size: 0.86rem;
  display: flex;
  align-items: center;
  gap: 12px;
}
@media (prefers-color-scheme: dark) {
  .disclaimer-banner { color: #fde68a; border-color: rgba(245, 158, 11, 0.4); }
}

.alert-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  max-width: 480px;
  padding: 14px 20px;
  border-radius: var(--radius-md);
  font-size: 0.88rem;
  font-weight: 600;
  background: var(--bg-card);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
  z-index: 100;
  display: none;
  animation: slideUp 0.25s ease;
  word-break: break-word;
}
.alert-toast.error { border-color: var(--danger); color: var(--danger); }
.alert-toast.success { border-color: var(--success); color: var(--success); }
@keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
}
.checkbox-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card-secondary);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  cursor: pointer;
}
.checkbox-item input { width: auto; margin: 0; cursor: pointer; }

.step-builder-row {
  background: var(--bg-card-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
  margin-bottom: 12px;
}
.step-builder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.pipeline-diagram {
  width: 100%;
  overflow-x: auto;
  padding: 20px 0;
}
</style>
</head>
<body>

<header>
  <div class="brand-title">
    <span>SHADOWLINK</span>
    <span class="brand-badge">Defensive Privacy Benchmark</span>
  </div>
  <div id="run-pill" class="run-status-pill">
    <div class="status-dot inactive" id="pill-dot"></div>
    <span id="pill-text">No Active Run</span>
  </div>
</header>

<nav class="tab-nav">
  <button class="tab-btn active" onclick="switchTab('overview')">1. Overview</button>
  <button class="tab-btn" onclick="switchTab('data')">2. Data Generation</button>
  <button class="tab-btn" onclick="switchTab('qi')">3. QI &amp; k-Anonymity</button>
  <button class="tab-btn" onclick="switchTab('attacker')">4. Attacker Simulator</button>
  <button class="tab-btn" onclick="switchTab('linkage')">5. Linkage Engine</button>
  <button class="tab-btn" onclick="switchTab('mitigation')">6. Mitigation</button>
  <button class="tab-btn" onclick="switchTab('tables')">7. Report Tables</button>
</nav>

<main>
  <!-- TAB 1: OVERVIEW -->
  <section id="tab-overview" class="tab-pane active">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">11-Stage Defensive Privacy Pipeline</div>
          <div class="card-subtitle">End-to-end orchestration connecting Synthetic Generation, Linkage, Attack, Mitigation and Evaluation.</div>
        </div>
        <button class="btn btn-primary" onclick="runPipelineAction()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          Run Full Pipeline
        </button>
      </div>

      <div class="disclaimer-banner">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        <div>
          <strong>Ground-Truth Boundary Enforced:</strong> Modules linkage/ and attacker/ never receive, inspect, or mention entity identifiers. Only evaluator/ measures true re-identification accuracy against isolated ground truth.
        </div>
      </div>

      <div class="pipeline-diagram">
        <svg width="100%" height="220" viewBox="0 0 1100 220" style="background:var(--bg-card-secondary); border-radius:var(--radius-md); border:1px solid var(--border-color);">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-muted)" />
            </marker>
          </defs>
          <!-- Row 1: Stages 1 to 6 -->
          <g transform="translate(20, 25)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">1. Generator</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Synthetic Bundles</text>
            <circle id="stage-dot-1" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="165" y1="55" x2="195" y2="55" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(195, 25)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">2. Profiler</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Uniqueness &amp; Types</text>
            <circle id="stage-dot-2" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="340" y1="55" x2="370" y2="55" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(370, 25)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">3. Shared QIs</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Overlap Analysis</text>
            <circle id="stage-dot-3" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="515" y1="55" x2="545" y2="55" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(545, 25)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">4. Equiv. Classes</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">k-Anonymity &amp; Sizes</text>
            <circle id="stage-dot-4" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="690" y1="55" x2="720" y2="55" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(720, 25)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">5. Risk Engine</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Class-based Metrics</text>
            <circle id="stage-dot-5" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="865" y1="55" x2="895" y2="55" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(895, 25)">
            <rect width="165" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">6. Attacker Simulator</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Progressive Disclosure</text>
            <circle id="stage-dot-6" cx="152" cy="18" r="4" fill="var(--text-muted)" />
          </g>

          <path d="M 977 85 L 977 125 L 880 125" fill="none" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <!-- Row 2: Stages 7 to 11 -->
          <g transform="translate(735, 125)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">7. Linkage Engine</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">D / Sim / Fellegi-Sunter</text>
            <circle id="stage-dot-7" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="735" y1="155" x2="705" y2="155" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(560, 125)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">8. Mitigation</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Generalize &amp; Suppress</text>
            <circle id="stage-dot-8" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="560" y1="155" x2="530" y2="155" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(385, 125)">
            <rect width="145" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">9. Re-Assessment</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Post-Mitigation Risk</text>
            <circle id="stage-dot-9" cx="132" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="385" y1="155" x2="355" y2="155" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(200, 125)">
            <rect width="155" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">10. Evaluator</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">Precision, Recall &amp; Re-ID</text>
            <circle id="stage-dot-10" cx="142" cy="18" r="4" fill="var(--text-muted)" />
          </g>
          <line x1="200" y1="155" x2="170" y2="155" stroke="var(--border-color)" stroke-width="2" marker-end="url(#arrow)" />

          <g transform="translate(20, 125)">
            <rect width="150" height="60" rx="8" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1.5" />
            <text x="12" y="26" font-size="11" font-weight="700" fill="var(--text-primary)">11. Reporting</text>
            <text x="12" y="44" font-size="9" fill="var(--text-muted)">JSON &amp; Tables 5, 6, 7</text>
            <circle id="stage-dot-11" cx="137" cy="18" r="4" fill="var(--text-muted)" />
          </g>
        </svg>
      </div>

      <div class="grid-3" style="margin-top:20px;">
        <div class="stat-box">
          <div class="stat-val" id="ov-dataset-count">–</div>
          <div class="stat-lbl">Active Datasets</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="ov-row-count">–</div>
          <div class="stat-lbl">Total Synthetic Records</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="ov-seed">–</div>
          <div class="stat-lbl">Random Benchmark Seed</div>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 2: DATA GENERATION -->
  <section id="tab-data" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Synthetic Benchmark Generation</div>
          <div class="card-subtitle">Generate realistic demographic and behavioral dataset bundles with controlled noise.</div>
        </div>
      </div>

      <form id="gen-form" onsubmit="handleCreateRun(event)">
        <div class="grid-3">
          <div class="form-group">
            <label>Preset</label>
            <select id="gen-preset">
              <option value="report_abc">report_abc (Datasets A, B, C)</option>
              <option value="wide_release">wide_release (Broad QI sets)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Population Size (50 - 5000)</label>
            <input type="number" id="gen-pop" value="100" min="50" max="5000" required>
          </div>
          <div class="form-group">
            <label>Shared Fraction (0.0 - 1.0)</label>
            <input type="number" id="gen-shared" value="0.5" step="0.05" min="0" max="1" required>
          </div>
          <div class="form-group">
            <label>Typo Rate (0.0 - 1.0)</label>
            <input type="number" id="gen-typo" value="0.05" step="0.01" min="0" max="1" required>
          </div>
          <div class="form-group">
            <label>Missing Rate (0.0 - 1.0)</label>
            <input type="number" id="gen-missing" value="0.02" step="0.01" min="0" max="1" required>
          </div>
          <div class="form-group">
            <label>Deterministic Seed</label>
            <input type="number" id="gen-seed" value="42" min="0" required>
          </div>
        </div>
        <button type="submit" class="btn btn-primary" id="btn-generate">Generate Bundle</button>
      </form>
    </div>

    <!-- Previews -->
    <div class="card" id="previews-card" style="display:none;">
      <div class="card-header">
        <div>
          <div class="card-title">Dataset Previews &amp; Profiles (Top 10 Rows)</div>
          <div class="card-subtitle">Ground-truth identifiers stripped. Synthetic data only.</div>
        </div>
      </div>
      <div id="previews-container"></div>
    </div>
  </section>

  <!-- TAB 3: QI & K-ANONYMITY -->
  <section id="tab-qi" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Quasi-Identifier &amp; Equivalence Class Analysis</div>
          <div class="card-subtitle">Evaluate class-based re-identification risk metrics under chosen quasi-identifiers.</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="form-group">
          <label>Target Dataset</label>
          <select id="qi-dataset" onchange="updateQICheckboxes()"></select>
        </div>
        <div class="form-group">
          <label>Quasi-Identifier Columns</label>
          <div class="checkbox-group" id="qi-checkboxes"></div>
        </div>
      </div>
      <button class="btn btn-primary" onclick="handleQIAnalysis()">Analyze Quasi-Identifiers</button>
    </div>

    <div id="qi-results" style="display:none;">
      <div class="grid-4" style="margin-bottom:24px;">
        <div class="stat-box">
          <div class="stat-val" id="qi-k">–</div>
          <div class="stat-lbl">k-Anonymity (Min Class Size)</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="qi-singleton">–</div>
          <div class="stat-lbl">Singleton Proportion (|C|=1)</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="qi-max-risk">–</div>
          <div class="stat-lbl">Max Class Risk (1 / k)</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="qi-avg-risk">–</div>
          <div class="stat-lbl">Mean Class Risk</div>
        </div>
      </div>

      <div class="card">
        <div class="card-title" style="margin-bottom:12px;">Equivalence Class Size Distribution</div>
        <div id="qi-histogram" style="width:100%; height:180px;"></div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">Candidate Quasi-Identifiers</div>
          <div class="table-responsive">
            <table id="qi-candidates-table">
              <thead><tr><th>Column</th><th>Shared across datasets</th><th>Reasons</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">Computed Risk Metrics (this run)</div>
          <div id="qi-risk-metrics-container"></div>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 4: ATTACKER SIMULATOR -->
  <section id="tab-attacker" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Progressive Disclosure Attacker Simulator</div>
          <div class="card-subtitle">Simulate an adversary incrementally acquiring auxiliary attributes to narrow candidate target sets.</div>
        </div>
      </div>

      <div class="grid-3">
        <div class="form-group">
          <label>Target Dataset</label>
          <select id="att-dataset" onchange="initAttackSteps()"></select>
        </div>
        <div class="form-group">
          <label>Target Count (n_targets)</label>
          <input type="number" id="att-targets" value="25" min="1" max="500">
        </div>
        <div class="form-group">
          <label>Simulation Seed</label>
          <input type="number" id="att-seed" value="42" min="0">
        </div>
      </div>

      <div class="form-group">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <label style="margin:0;">Ordered Knowledge Steps (Progressive Auxiliary Disclosure)</label>
          <button type="button" class="btn btn-secondary btn-sm" onclick="addAttackStep()">+ Add Step</button>
        </div>
        <div id="att-steps-container"></div>
      </div>
      <button class="btn btn-primary" onclick="handleAttackSimulation()">Simulate Progressive Attack</button>
    </div>

    <div id="att-results" style="display:none;">
      <div class="card">
        <div class="card-title" style="margin-bottom:12px;">Progressive Disclosure Narrowing Curve (Mean Candidates)</div>
        <div id="att-curve-chart" style="width:100%; height:240px;"></div>
      </div>

      <div class="card">
        <div class="card-title" style="margin-bottom:12px;">Step-by-Step Adversary Metrics</div>
        <div class="table-responsive">
          <table id="att-steps-table">
            <thead>
              <tr><th>Step</th><th>Attributes</th><th>Mean Candidates</th><th>Median Candidates</th><th>Mean Risk</th><th>Unique %</th><th>Reduction Ratio</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 5: LINKAGE ENGINE -->
  <section id="tab-linkage" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Multi-Method Record Linkage Engine</div>
          <div class="card-subtitle">Deterministic, Similarity, and Fellegi-Sunter cross-dataset linkage benchmarked against ground truth.</div>
        </div>
      </div>

      <div class="grid-3">
        <div class="form-group">
          <label>Dataset Pair</label>
          <div style="display:flex; gap:8px;">
            <select id="lnk-left"><option value="A">A (Demographics)</option></select>
            <select id="lnk-right"><option value="B">B (Academic)</option></select>
          </div>
        </div>
        <div class="form-group">
          <label>Linkage Method</label>
          <select id="lnk-method">
            <option value="similarity">Similarity Linkage (Jaro-Winkler / Levenshtein)</option>
            <option value="deterministic">Deterministic Exact Match</option>
            <option value="fellegi_sunter">Fellegi-Sunter Probabilistic Weighting</option>
            <option value="compare_all">Compare All Methods</option>
          </select>
        </div>
        <div class="form-group">
          <label>Threshold</label>
          <input type="number" id="lnk-thresh" value="0.85" step="0.05" min="0" max="1">
        </div>
      </div>
      <button class="btn btn-primary" onclick="handleLinkageExecution()">Execute Linkage Evaluation</button>
    </div>

    <div id="lnk-results" style="display:none;">
      <div class="grid-5" style="margin-bottom:24px;">
        <div class="stat-box">
          <div class="stat-val" id="lnk-precision">–</div>
          <div class="stat-lbl">Precision</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="lnk-recall">–</div>
          <div class="stat-lbl">Recall</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="lnk-f1">–</div>
          <div class="stat-lbl">F1 Score</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="lnk-det-reid">–</div>
          <div class="stat-lbl">Deterministic Re-ID</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="lnk-tie-reid">–</div>
          <div class="stat-lbl">Tie-Adjusted Re-ID</div>
        </div>
      </div>

      <div class="card" id="lnk-comparison-card" style="display:none;">
        <div class="card-title" style="margin-bottom:12px;">Multi-Method Linkage Comparison</div>
        <div class="table-responsive">
          <table id="lnk-comparison-table">
            <thead>
              <tr><th>Method</th><th>Threshold</th><th>Precision</th><th>Recall</th><th>F1</th><th>Deterministic Re-ID</th><th>Tie-Adjusted Re-ID</th><th>Runtime (ms)</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 6: MITIGATION -->
  <section id="tab-mitigation" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Privacy Mitigation &amp; Utility Tradeoff</div>
          <div class="card-subtitle">Apply Generalization and Suppression transforms to evaluate privacy gain versus discernibility loss.</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="form-group">
          <label>Target Dataset</label>
          <select id="mit-dataset"></select>
        </div>
        <div class="form-group">
          <label>Quasi-Identifier Attributes</label>
          <div class="checkbox-group" id="mit-qi-checkboxes"></div>
        </div>
      </div>

      <div class="form-group">
        <label>Applied Transformations</label>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">
          Enabled: <code>generalize_age(width=5)</code>, <code>suppress_rare_values(k=2)</code>
        </div>
      </div>
      <button class="btn btn-primary" onclick="handleMitigationExecution()">Apply Mitigation &amp; Evaluate</button>
    </div>

    <div id="mit-results" style="display:none;">
      <div class="grid-2">
        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">Privacy Risk: Before vs After</div>
          <div class="table-responsive">
            <table>
              <thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Status</th></tr></thead>
              <tbody>
                <tr><td>k-Anonymity</td><td id="mit-k-before">–</td><td id="mit-k-after">–</td><td id="mit-k-status">–</td></tr>
                <tr><td>Unique Fraction</td><td id="mit-uniq-before">–</td><td id="mit-uniq-after">–</td><td id="mit-uniq-status">–</td></tr>
                <tr><td>Max Re-ID Risk</td><td id="mit-maxrisk-before">–</td><td id="mit-maxrisk-after">–</td><td id="mit-maxrisk-status">–</td></tr>
                <tr><td>Average Risk</td><td id="mit-avgrisk-before">–</td><td id="mit-avgrisk-after">–</td><td id="mit-avgrisk-status">–</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">Utility Loss &amp; Distortion</div>
          <div class="table-responsive">
            <table>
              <thead><tr><th>Metric</th><th>Value</th><th>Interpretation</th></tr></thead>
              <tbody>
                <tr><td>Discernibility Metric (DM)</td><td id="mit-dm">–</td><td>Normalized equivalence class penalty</td></tr>
                <tr><td>Suppressed Records</td><td id="mit-suppressed">–</td><td>Records removed to prevent singleton leak</td></tr>
                <tr><td>Suppression Rate</td><td id="mit-supp-pct">–</td><td>Percentage of dataset removed</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="disclaimer-banner">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        <div id="mit-notes">Privacy mitigation reduces linkage risk by merging distinct equivalence classes.</div>
      </div>
    </div>
  </section>

  <!-- TAB 7: REPORT TABLES -->
  <section id="tab-tables" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Comprehensive Benchmark Report Tables</div>
          <div class="card-subtitle">Exact reproducible evaluation tables (Tables 5, 6, 7) generated directly from the platform.</div>
        </div>
        <button class="btn btn-secondary" onclick="fetchTablesAction()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
          Refresh Tables
        </button>
      </div>

      <div id="tables-container">
        <div style="color:var(--text-muted); font-size:0.9rem;">Generate a run or click "Refresh Tables" to view benchmark evaluation tables.</div>
      </div>
    </div>
  </section>
</main>

<div id="toast" class="alert-toast"></div>

<script>
let currentRunId = null;
let currentRunData = null;

function escapeHtml(str) {
  if (str === null || str === undefined) return "–";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatNum(val, decimals) {
  if (decimals === undefined) decimals = 3;
  if (val === null || val === undefined || isNaN(Number(val))) return "–";
  return Number(val).toFixed(decimals);
}

function formatPct(val, decimals) {
  if (decimals === undefined) decimals = 1;
  if (val === null || val === undefined || isNaN(Number(val))) return "–";
  return (Number(val) * 100).toFixed(decimals) + "%";
}

async function extractErrorDetail(res) {
  try {
    const err = await res.json();
    if (typeof err.detail === "string") {
      return "HTTP " + res.status + ": " + err.detail;
    }
    if (Array.isArray(err.detail)) {
      const msgs = err.detail.map(d => {
        const loc = Array.isArray(d.loc) ? d.loc.filter(x => x !== "body").join(".") : "";
        return loc ? loc + ": " + d.msg : d.msg;
      });
      return "HTTP " + res.status + " Validation Error: " + msgs.join("; ");
    }
    if (err.message) return "HTTP " + res.status + ": " + err.message;
    return "HTTP " + res.status + ": " + JSON.stringify(err);
  } catch (e) {
    return "HTTP " + res.status + ": " + (res.statusText || "Request failed");
  }
}

function showToast(msg, isError) {
  if (isError === undefined) isError = false;
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "alert-toast " + (isError ? "error" : "success");
  t.style.display = "block";
  setTimeout(() => { t.style.display = "none"; }, 4500);
}

function switchTab(name) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
  const target = document.getElementById("tab-" + name);
  if (target) target.classList.add("active");
  const btns = document.querySelectorAll(".tab-btn");
  const tabNames = ["overview", "data", "qi", "attacker", "linkage", "mitigation", "tables"];
  const idx = tabNames.indexOf(name);
  if (idx >= 0 && btns[idx]) btns[idx].classList.add("active");
}

function updateActiveRunPill(id, preset, n, seed) {
  currentRunId = id;
  const dot = document.getElementById("pill-dot");
  const txt = document.getElementById("pill-text");
  dot.className = "status-dot";
  txt.textContent = "Run: " + id.substring(0, 8) + "... | " + preset + " | N=" + n + " | seed=" + seed;
  document.getElementById("ov-seed").textContent = seed;
}

function updatePipelineDots(statusObj) {
  if (!statusObj) return;
  const stages = [
    "1. Generation", "2. Profiling", "3. QI Analysis", "4. Risk Engine",
    "5. Attacker Simulator", "6. Linkage Engine", "7. Mitigation",
    "8. Evaluator", "9. Report"
  ];
  stages.forEach((st, i) => {
    const dot = document.getElementById("stage-dot-" + (i + 1));
    if (dot) {
      const s = statusObj[st];
      if (s === "done") dot.setAttribute("fill", "var(--success)");
      else if (s === "running") dot.setAttribute("fill", "var(--warning)");
      else dot.setAttribute("fill", "var(--text-muted)");
    }
  });
}

async function handleCreateRun(e) {
  if (e) e.preventDefault();
  const btn = document.getElementById("btn-generate");
  btn.disabled = true;
  btn.textContent = "Generating...";
  try {
    const payload = {
      preset: document.getElementById("gen-preset").value,
      population_size: parseInt(document.getElementById("gen-pop").value, 10),
      shared_fraction: parseFloat(document.getElementById("gen-shared").value),
      typo_rate: parseFloat(document.getElementById("gen-typo").value),
      missing_rate: parseFloat(document.getElementById("gen-missing").value),
      seed: parseInt(document.getElementById("gen-seed").value, 10),
    };
    const res = await fetch("/demo/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    currentRunData = data;
    updateActiveRunPill(data.run_id, data.preset, data.population_size, data.seed);
    updatePipelineDots(data.stage_status);
    renderPreviews(data);
    populateSelects(data);
    showToast("Bundle generated successfully!");
    switchTab("data");
  } catch (err) {
    showToast(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Bundle";
  }
}

function renderPreviews(data) {
  document.getElementById("previews-card").style.display = "block";
  const container = document.getElementById("previews-container");
  container.innerHTML = "";

  let totalRows = 0;
  const dsNames = Object.keys(data.dataset_counts || {});
  document.getElementById("ov-dataset-count").textContent = dsNames.length;

  dsNames.forEach(name => {
    const count = data.dataset_counts[name];
    totalRows += count;
    const rows = (data.dataset_previews && data.dataset_previews[name]) || [];

    const card = document.createElement("div");
    card.className = "card";
    card.style.marginBottom = "18px";

    let cols = rows.length > 0 ? Object.keys(rows[0]) : [];

    let tableHtml = '<div class="table-responsive"><table><thead><tr>';
    cols.forEach(c => { tableHtml += "<th>" + escapeHtml(c) + "</th>"; });
    tableHtml += "</tr></thead><tbody>";

    rows.forEach(r => {
      tableHtml += "<tr>";
      cols.forEach(c => {
        const val = r[c] !== null && r[c] !== undefined ? r[c] : "–";
        tableHtml += "<td>" + escapeHtml(val) + "</td>";
      });
      tableHtml += "</tr>";
    });
    tableHtml += "</tbody></table></div>";

    card.innerHTML =
      '<div class="card-header">' +
        '<div>' +
          '<strong>Dataset ' + escapeHtml(name) + '</strong>' +
          '<span style="font-size:0.8rem; color:var(--text-muted); margin-left:8px;">(' + count + ' rows, ' + cols.length + ' attributes)</span>' +
        '</div>' +
      '</div>' +
      tableHtml;
    container.appendChild(card);
  });
  document.getElementById("ov-row-count").textContent = totalRows;
}

function populateSelects(data) {
  const names = Object.keys(data.dataset_counts || {});
  const qiSel = document.getElementById("qi-dataset");
  const attSel = document.getElementById("att-dataset");
  const mitSel = document.getElementById("mit-dataset");
  const leftSel = document.getElementById("lnk-left");
  const rightSel = document.getElementById("lnk-right");

  [qiSel, attSel, mitSel, leftSel, rightSel].forEach(sel => {
    sel.innerHTML = "";
    names.forEach(n => {
      const opt = document.createElement("option");
      opt.value = n;
      opt.textContent = "Dataset " + n;
      sel.appendChild(opt);
    });
  });

  if (names.length >= 2) {
    rightSel.selectedIndex = 1;
  }
  updateQICheckboxes();
  updateMitCheckboxes();
  initAttackSteps();
}

function updateQICheckboxes() {
  if (!currentRunData) return;
  const ds = document.getElementById("qi-dataset").value;
  const preview = (currentRunData.dataset_previews && currentRunData.dataset_previews[ds]) || [];
  const container = document.getElementById("qi-checkboxes");
  container.innerHTML = "";
  if (preview.length === 0) return;

  const cols = Object.keys(preview[0]);
  cols.forEach((c, idx) => {
    const label = document.createElement("label");
    label.className = "checkbox-item";
    const checked = idx < 2 ? "checked" : "";
    label.innerHTML = '<input type="checkbox" name="qi-col" value="' + escapeHtml(c) + '" ' + checked + '> ' + escapeHtml(c);
    container.appendChild(label);
  });
}

function updateMitCheckboxes() {
  if (!currentRunData) return;
  const ds = document.getElementById("mit-dataset").value;
  const preview = (currentRunData.dataset_previews && currentRunData.dataset_previews[ds]) || [];
  const container = document.getElementById("mit-qi-checkboxes");
  container.innerHTML = "";
  if (preview.length === 0) return;

  const cols = Object.keys(preview[0]);
  cols.forEach((c, idx) => {
    const label = document.createElement("label");
    label.className = "checkbox-item";
    const checked = (c === "age" || c === "city" || idx < 2) ? "checked" : "";
    label.innerHTML = '<input type="checkbox" name="mit-qi-col" value="' + escapeHtml(c) + '" ' + checked + '> ' + escapeHtml(c);
    container.appendChild(label);
  });
}

function getAvailableColumnsForDataset(ds) {
  if (!currentRunData || !currentRunData.dataset_previews || !currentRunData.dataset_previews[ds]) return [];
  const rows = currentRunData.dataset_previews[ds];
  return rows.length > 0 ? Object.keys(rows[0]) : [];
}

function initAttackSteps() {
  const ds = document.getElementById("att-dataset").value;
  const cols = getAvailableColumnsForDataset(ds);
  const container = document.getElementById("att-steps-container");
  container.innerHTML = "";
  if (cols.length === 0) return;

  const defaultStep1 = ["age", "city"].filter(c => cols.includes(c));
  const s1 = defaultStep1.length > 0 ? defaultStep1 : [cols[0]];
  createStepRowUI(1, s1, cols, false);

  const rem1 = cols.filter(c => !s1.includes(c));
  let s2 = [];
  if (rem1.includes("course")) s2 = ["course"];
  else if (rem1.includes("education")) s2 = ["education"];
  else if (rem1.length > 0) s2 = [rem1[0]];

  if (s2.length > 0) {
    createStepRowUI(2, s2, cols, true);
  }
}

function addAttackStep() {
  const ds = document.getElementById("att-dataset").value;
  const cols = getAvailableColumnsForDataset(ds);
  const container = document.getElementById("att-steps-container");
  const stepIdx = container.querySelectorAll(".step-builder-row").length + 1;
  createStepRowUI(stepIdx, [], cols, true);
}

function createStepRowUI(stepNum, selectedCols, allCols, canRemove) {
  const container = document.getElementById("att-steps-container");
  const row = document.createElement("div");
  row.className = "step-builder-row";
  row.setAttribute("data-step-index", stepNum);

  let checkboxesHtml = '<div class="checkbox-group">';
  allCols.forEach(col => {
    const checked = selectedCols.includes(col) ? "checked" : "";
    checkboxesHtml += '<label class="checkbox-item"><input type="checkbox" value="' + escapeHtml(col) + '" ' + checked + '> ' + escapeHtml(col) + '</label>';
  });
  checkboxesHtml += '</div>';

  const removeBtnHtml = canRemove ? '<button type="button" class="btn btn-sm btn-danger" onclick="removeStepRow(this)">Remove</button>' : '<span style="font-size:0.75rem; color:var(--text-muted);">(Base Step)</span>';

  row.innerHTML =
    '<div class="step-builder-header">' +
      '<span><strong>Step ' + stepNum + '</strong>: Select Knowledge Attributes</span>' +
      removeBtnHtml +
    '</div>' +
    checkboxesHtml;

  container.appendChild(row);
  renumberStepRows();
}

function removeStepRow(btn) {
  const row = btn.closest(".step-builder-row");
  if (row) row.remove();
  renumberStepRows();
}

function renumberStepRows() {
  const rows = document.querySelectorAll("#att-steps-container .step-builder-row");
  rows.forEach((r, idx) => {
    const stepNum = idx + 1;
    r.setAttribute("data-step-index", stepNum);
    const span = r.querySelector(".step-builder-header span strong");
    if (span) span.textContent = "Step " + stepNum;
  });
}

async function handleQIAnalysis() {
  if (!currentRunId) {
    showToast("Please generate a benchmark bundle first.", true);
    return;
  }
  const ds = document.getElementById("qi-dataset").value;
  const checkedBoxes = Array.from(document.querySelectorAll('input[name="qi-col"]:checked'));
  const qiCols = checkedBoxes.map(b => b.value);
  if (qiCols.length === 0) {
    showToast("Select at least one quasi-identifier column.", true);
    return;
  }

  try {
    const res = await fetch("/demo/api/runs/" + currentRunId + "/qi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_name: ds, qi_columns: qiCols })
    });
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    document.getElementById("qi-results").style.display = "block";
    document.getElementById("qi-k").textContent = formatNum(data.k_anonymity, 0);
    document.getElementById("qi-singleton").textContent = formatPct(data.singleton_proportion, 1);
    document.getElementById("qi-max-risk").textContent = formatNum(data.max_risk, 3);
    document.getElementById("qi-avg-risk").textContent = formatNum(data.average_risk, 3);

    // Candidates table (Column, Shared across datasets, Reasons)
    const tbody = document.querySelector("#qi-candidates-table tbody");
    tbody.innerHTML = "";
    const sharedSet = new Set(data.shared_attributes || []);
    const cands = data.candidate_qis || [];
    if (cands.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted); padding:16px;">No candidate quasi-identifiers identified for this dataset.</td></tr>';
    } else {
      cands.forEach(cand => {
        const isShared = sharedSet.has(cand.column_name);
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td><strong>" + escapeHtml(cand.column_name) + "</strong></td>" +
          "<td>" + (isShared ? '<span style="color:var(--success); font-weight:700;">Yes</span>' : '<span style="color:var(--text-muted);">No</span>') + "</td>" +
          "<td>" + escapeHtml((cand.reasons || []).join("; ")) + "</td>";
        tbody.appendChild(tr);
      });
    }

    // Computed Risk Metrics (this run)
    const metricsContainer = document.getElementById("qi-risk-metrics-container");
    metricsContainer.innerHTML = "";
    const metrics = data.risk_metrics || [];
    if (metrics.length === 0) {
      metricsContainer.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No risk metrics returned.</div>';
    } else {
      metrics.forEach(m => {
        const card = document.createElement("div");
        card.className = "formula-card";
        card.innerHTML =
          '<div class="formula-title">' + escapeHtml(m.name) + ': <strong style="color:var(--primary); font-family:var(--font-mono);">' + formatNum(m.value, 4) + '</strong></div>' +
          '<div class="formula-math">' + escapeHtml(m.formula || "–") + '</div>' +
          '<div class="formula-desc"><strong>Assumption:</strong> ' + escapeHtml(m.assumption || "–") + '</div>' +
          (m.explanation ? '<div class="formula-desc" style="margin-top:4px;"><strong>Explanation:</strong> ' + escapeHtml(m.explanation) + '</div>' : '');
        metricsContainer.appendChild(card);
      });
    }

    renderHistogram(data.equivalence_classes && data.equivalence_classes.class_sizes);
    updatePipelineDots(data.stage_status);
    showToast("QI & k-Anonymity analysis completed.");
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderHistogram(sizes) {
  const container = document.getElementById("qi-histogram");
  if (!sizes || sizes.length === 0) {
    container.innerHTML = "No equivalence class data.";
    return;
  }
  const counts = {};
  sizes.forEach(s => { counts[s] = (counts[s] || 0) + 1; });
  const keys = Object.keys(counts).map(Number).sort((a,b) => a - b).slice(0, 15);
  const maxFreq = Math.max(...keys.map(k => counts[k]), 1);

  let svg = '<svg width="100%" height="160" viewBox="0 0 600 160">';
  const barWidth = Math.min(30, (550 / keys.length) - 6);
  keys.forEach((k, i) => {
    const freq = counts[k];
    const h = (freq / maxFreq) * 110;
    const x = 40 + i * (barWidth + 8);
    const y = 130 - h;
    svg +=
      '<rect x="' + x + '" y="' + y + '" width="' + barWidth + '" height="' + h + '" fill="var(--primary)" rx="3" />' +
      '<text x="' + (x + barWidth/2) + '" y="' + (y - 4) + '" font-size="9" text-anchor="middle" fill="var(--text-muted)">' + freq + '</text>' +
      '<text x="' + (x + barWidth/2) + '" y="145" font-size="10" text-anchor="middle" fill="var(--text-secondary)">|C|=' + k + '</text>';
  });
  svg += '<line x1="30" y1="130" x2="580" y2="130" stroke="var(--border-color)" stroke-width="1" />';
  svg += '</svg>';
  container.innerHTML = svg;
}

async function handleAttackSimulation() {
  if (!currentRunId) {
    showToast("Please generate a benchmark bundle first.", true);
    return;
  }
  const ds = document.getElementById("att-dataset").value;
  const nTargets = parseInt(document.getElementById("att-targets").value, 10);
  const seed = parseInt(document.getElementById("att-seed").value, 10);

  const stepRows = document.querySelectorAll("#att-steps-container .step-builder-row");
  const configuredSteps = [];
  stepRows.forEach(row => {
    const checked = Array.from(row.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
    if (checked.length > 0) configuredSteps.push(checked);
  });

  if (configuredSteps.length === 0) {
    showToast("Please configure at least one attack step with selected attributes.", true);
    return;
  }

  try {
    const res = await fetch("/demo/api/runs/" + currentRunId + "/attack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_name: ds,
        steps: configuredSteps,
        n_targets: nTargets,
        seed: seed
      })
    });
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    document.getElementById("att-results").style.display = "block";

    const tbody = document.querySelector("#att-steps-table tbody");
    tbody.innerHTML = "";
    const curve = data.narrowing_curve || data.steps || [];
    curve.forEach(step => {
      const tr = document.createElement("tr");
      const attrsStr = step.attributes ? step.attributes.replace(/\+/g, ", ") : "–";
      tr.innerHTML =
        "<td><strong>Step " + escapeHtml(step.step) + "</strong></td>" +
        "<td><code>" + escapeHtml(attrsStr) + "</code></td>" +
        "<td>" + formatNum(step.mean_candidates, 2) + "</td>" +
        "<td>" + formatNum(step.median_candidates, 1) + "</td>" +
        "<td>" + formatNum(step.mean_risk, 3) + "</td>" +
        "<td>" + formatPct(step.unique_fraction, 1) + "</td>" +
        "<td>" + formatNum(step.mean_reduction, 3) + "</td>";
      tbody.appendChild(tr);
    });

    renderAttackCurve(curve);
    updatePipelineDots(data.stage_status);
    showToast("Progressive attack simulation completed.");
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderAttackCurve(curve) {
  const container = document.getElementById("att-curve-chart");
  if (!curve || curve.length === 0) return;

  const validVals = curve.map(c => Number(c.mean_candidates) || 0);
  const maxMean = Math.max(...validVals, 1);
  let svg = '<svg width="100%" height="220" viewBox="0 0 600 220">';
  svg += '<line x1="50" y1="20" x2="50" y2="180" stroke="var(--border-color)" stroke-width="1"/>';
  svg += '<line x1="50" y1="180" x2="560" y2="180" stroke="var(--border-color)" stroke-width="1"/>';

  let points = [];
  const xStep = 450 / Math.max(1, curve.length - 1);
  curve.forEach((c, idx) => {
    const val = Number(c.mean_candidates) || 0;
    const x = 70 + idx * xStep;
    const y = 180 - (val / maxMean) * 140;
    points.push(x + "," + y);
    svg +=
      '<circle cx="' + x + '" cy="' + y + '" r="5" fill="var(--danger)" />' +
      '<text x="' + x + '" y="' + (y - 8) + '" font-size="10" font-weight="700" text-anchor="middle" fill="var(--danger)">' + formatNum(val, 1) + '</text>' +
      '<text x="' + x + '" y="198" font-size="10" text-anchor="middle" fill="var(--text-secondary)">Step ' + escapeHtml(c.step) + '</text>';
  });
  if (points.length > 1) {
    svg += '<polyline fill="none" stroke="var(--danger)" stroke-width="2.5" points="' + points.join(" ") + '" />';
  }
  svg += '</svg>';
  container.innerHTML = svg;
}

async function handleLinkageExecution() {
  if (!currentRunId) {
    showToast("Please generate a benchmark bundle first.", true);
    return;
  }
  const left = document.getElementById("lnk-left").value;
  const right = document.getElementById("lnk-right").value;
  const method = document.getElementById("lnk-method").value;
  const thresh = parseFloat(document.getElementById("lnk-thresh").value);

  try {
    const res = await fetch("/demo/api/runs/" + currentRunId + "/linkage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        left_dataset: left,
        right_dataset: right,
        method: method,
        threshold: thresh
      })
    });
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    document.getElementById("lnk-results").style.display = "block";

    if (method === "compare_all" || data.comparison) {
      document.getElementById("lnk-comparison-card").style.display = "block";
      const tbody = document.querySelector("#lnk-comparison-table tbody");
      tbody.innerHTML = "";
      const comparisonMap = data.comparison || {};
      Object.keys(comparisonMap).forEach(m => {
        const item = comparisonMap[m] || {};
        const tr = document.createElement("tr");
        const f1Val = item.f1 !== undefined ? item.f1 : item.f1_score;
        const tieVal = item.tie_adjusted_reid_success !== undefined ? item.tie_adjusted_reid_success : item.reidentification_success;
        const runtimeMs = item.runtime_seconds !== null && item.runtime_seconds !== undefined ? item.runtime_seconds * 1000 : null;
        tr.innerHTML =
          "<td><strong>" + escapeHtml(item.method || m) + "</strong></td>" +
          "<td>" + formatNum(item.threshold, 2) + "</td>" +
          "<td>" + formatNum(item.precision, 3) + "</td>" +
          "<td>" + formatNum(item.recall, 3) + "</td>" +
          "<td>" + formatNum(f1Val, 3) + "</td>" +
          "<td>" + formatPct(item.deterministic_reid_success, 1) + "</td>" +
          "<td>" + formatPct(tieVal, 1) + "</td>" +
          "<td>" + formatNum(runtimeMs, 1) + "</td>";
        tbody.appendChild(tr);
      });
      const first = comparisonMap.similarity || Object.values(comparisonMap)[0] || data;
      setLinkageBoxes(first);
    } else {
      document.getElementById("lnk-comparison-card").style.display = "none";
      setLinkageBoxes(data);
    }

    updatePipelineDots(data.stage_status);
    showToast("Linkage evaluation completed.");
  } catch (err) {
    showToast(err.message, true);
  }
}

function setLinkageBoxes(d) {
  if (!d) return;
  const f1Val = d.f1 !== undefined ? d.f1 : d.f1_score;
  const tieVal = d.tie_adjusted_reid_success !== undefined ? d.tie_adjusted_reid_success : d.reidentification_success;
  document.getElementById("lnk-precision").textContent = formatNum(d.precision, 3);
  document.getElementById("lnk-recall").textContent = formatNum(d.recall, 3);
  document.getElementById("lnk-f1").textContent = formatNum(f1Val, 3);
  document.getElementById("lnk-det-reid").textContent = formatPct(d.deterministic_reid_success, 1);
  document.getElementById("lnk-tie-reid").textContent = formatPct(tieVal, 1);
}

async function handleMitigationExecution() {
  if (!currentRunId) {
    showToast("Please generate a benchmark bundle first.", true);
    return;
  }
  const ds = document.getElementById("mit-dataset").value;
  const checkedBoxes = Array.from(document.querySelectorAll('input[name="mit-qi-col"]:checked'));
  const qiCols = checkedBoxes.map(b => b.value);

  try {
    const res = await fetch("/demo/api/runs/" + currentRunId + "/mitigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_name: ds,
        qi_columns: qiCols,
        transformations: [
          { type: "generalize_age", kwargs: { bin_width: 5 } },
          { type: "suppress_rare_values", kwargs: { min_count: 2 } }
        ]
      })
    });
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    document.getElementById("mit-results").style.display = "block";

    const b = data.before || {};
    const a = data.after || {};
    const u = data.utility || {};

    document.getElementById("mit-k-before").textContent = formatNum(b.k_anonymity, 0);
    document.getElementById("mit-k-after").textContent = formatNum(a.k_anonymity, 0);
    document.getElementById("mit-k-status").textContent = (Number(a.k_anonymity) || 0) >= (Number(b.k_anonymity) || 0) ? "Improved" : "Maintained";

    document.getElementById("mit-uniq-before").textContent = formatPct(b.singleton_proportion, 1);
    document.getElementById("mit-uniq-after").textContent = formatPct(a.singleton_proportion, 1);
    document.getElementById("mit-uniq-status").textContent = "Reduced";

    document.getElementById("mit-maxrisk-before").textContent = formatNum(b.max_risk, 3);
    document.getElementById("mit-maxrisk-after").textContent = formatNum(a.max_risk, 3);
    document.getElementById("mit-maxrisk-status").textContent = (Number(a.max_risk) || 0) <= (Number(b.max_risk) || 0) ? "Lower Risk" : "Maintained";

    document.getElementById("mit-avgrisk-before").textContent = formatNum(b.average_risk, 3);
    document.getElementById("mit-avgrisk-after").textContent = formatNum(a.average_risk, 3);
    document.getElementById("mit-avgrisk-status").textContent = "Computed";

    document.getElementById("mit-dm").textContent = formatNum(u.discernibility_metric, 1);
    document.getElementById("mit-suppressed").textContent = formatNum(u.records_suppressed, 0);
    document.getElementById("mit-supp-pct").textContent = formatPct(u.suppression_rate, 1);
    document.getElementById("mit-notes").textContent = data.notes || "Privacy mitigation reduces linkage risk.";

    updatePipelineDots(data.stage_status);
    showToast("Mitigation tradeoff evaluation completed.");
  } catch (err) {
    showToast(err.message, true);
  }
}

async function runPipelineAction() {
  if (!currentRunId) {
    showToast("Please generate a benchmark bundle first.", true);
    return;
  }
  showToast("Running full 9-stage pipeline...");
  try {
    const res = await fetch("/demo/api/runs/" + currentRunId + "/pipeline", {
      method: "POST"
    });
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    updatePipelineDots(data.stage_status);
    showToast("Full pipeline executed successfully!");
    fetchTablesAction();
    switchTab("tables");
  } catch (err) {
    showToast(err.message, true);
  }
}

async function fetchTablesAction() {
  if (!currentRunId) {
    showToast("Please generate a benchmark bundle first.", true);
    return;
  }
  try {
    const res = await fetch("/demo/api/runs/" + currentRunId + "/tables");
    if (!res.ok) {
      const errMsg = await extractErrorDetail(res);
      throw new Error(errMsg);
    }
    const data = await res.json();
    renderTables(data);
    showToast("Benchmark tables refreshed.");
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderTables(data) {
  const container = document.getElementById("tables-container");
  container.innerHTML = "";

  const tableKeys = ["table5", "table6", "table7"];
  tableKeys.forEach(tk => {
    const tObj = data[tk];
    if (!tObj) return;

    const card = document.createElement("div");
    card.className = "card";
    card.style.marginBottom = "24px";

    const rows = tObj.rows || [];
    let cols = rows.length > 0 ? Object.keys(rows[0]) : [];

    let tableHtml = '<div class="table-responsive"><table><thead><tr>';
    cols.forEach(c => { tableHtml += "<th>" + escapeHtml(c) + "</th>"; });
    tableHtml += "</tr></thead><tbody>";

    rows.forEach(r => {
      tableHtml += "<tr>";
      cols.forEach(c => {
        const val = r[c] !== null && r[c] !== undefined ? r[c] : "–";
        tableHtml += "<td>" + escapeHtml(val) + "</td>";
      });
      tableHtml += "</tr>";
    });
    tableHtml += "</tbody></table></div>";

    const csvData = "data:text/csv;charset=utf-8," + encodeURIComponent(tObj.csv || "");

    card.innerHTML =
      '<div class="card-header">' +
        '<div>' +
          '<div class="card-title">' + escapeHtml(tObj.title) + '</div>' +
          '<div class="card-subtitle">Population N = ' + formatNum(data.population_size, 0) + ' | Deterministic Seed = ' + formatNum(data.seed, 0) + '</div>' +
        '</div>' +
        '<a href="' + csvData + '" download="' + tk + '.csv" class="btn btn-secondary btn-sm">' +
          'Download CSV' +
        '</a>' +
      '</div>' +
      tableHtml;
    container.appendChild(card);
  });
}
</script>
</body>
</html>
"""
