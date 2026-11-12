# SHADOWLINK — Privacy Re-identification Risk Assessment Platform

> **"Your data may be anonymous. Your shadow isn't."**

## Purpose and Safety Boundary

SHADOWLINK is an end-to-end **defensive** privacy-engineering and record-linkage platform. It measures how risky it is to release "anonymised" tabular datasets (direct identifiers removed, but quasi-identifiers such as age, city, and course remain), quantifies how risk changes after applying mitigation strategies, simulates real-world attacker re-identification capabilities under progressive attribute disclosure, and benchmarks record linkage accuracy against mathematical ground truth. All processing is strictly confined to synthetic and hand-crafted datasets; SHADOWLINK never accepts or processes real personal data, never makes external network calls, and enforces a strict boundary where ground-truth identity keys never leave the server or reach user-facing interfaces.

> **Synthetic Data Requirement**: The profile endpoint (`POST /profile`) stores top-5 categorical values from the dataset in the database for distribution profiling. Consequently, it must only be used with synthetic data, never real personal data.

## Team Contributions & Module Ownership

The platform was designed and developed across two core module groups:

* **Pratik Prasad**:
  * **Data Profiler** (`shadowlink.profiler`): Schema profiling, missingness, uniqueness, cardinality, and distribution summaries.
  * **QI Analyser** (`shadowlink.qi_analyser`): Quasi-identifier candidate detection, shared attributes, and equivalence class computation.
  * **Risk Engine** (`shadowlink.risk`): Class-level risk ($k$-anonymity, $l$-diversity, $t$-closeness), candidate-set risk, and discernibility metric.
  * **Mitigation Engine** (`shadowlink.mitigation`): Generalization hierarchies, binning, spatial coarsening, suppression, and privacy-utility tradeoff analysis.
* **Satyam Pathak**:
  * **Synthetic Data Generator** (`shadowlink.generator`): Latent population modeling, perturbation, typographical noise, and multi-dataset bundle generation.
  * **Linkage Engine** (`shadowlink.linkage`): Deterministic exact matching, similarity matching (Levenshtein, Jaro, Jaro-Winkler), Fellegi-Sunter probabilistic linkage, and blocking.
  * **Attacker Simulator** (`shadowlink.attacker`): Progressive auxiliary attribute disclosure modeling, candidate set narrowing curves, and prosecutor re-identification simulations.
  * **Evaluator** (`shadowlink.evaluator`): Ground-truth boundary evaluation, precision, recall, F1, calibration, and benchmark experiment suites (Tables 5, 6, 7).

*An AI coding assistant was used during development, and all code, architecture, algorithms, and documentation were reviewed and verified by the authors.*

## Pipeline Stages

The platform connects all modules into a unified 9-stage pipeline (Figure 1 in the project architecture):

1. **Synthetic Generation**: Synthesize multi-source datasets ($A, B, C$) from a latent population with controlled noise.
2. **Data Profiling**: Compute per-column distributions, missingness, and cardinality metrics without ground truth.
3. **QI Identification**: Detect candidate quasi-identifiers and compute cross-dataset schema overlap.
4. **Equivalence & Class Risk**: Partition records into equivalence classes and compute baseline $k$-anonymity and class-level re-identification risk.
5. **Attacker Simulation**: Model an adversary disclosing auxiliary attributes step-by-step ($|C| \to 1$) to compute candidate-set risk.
6. **Record Linkage**: Execute deterministic, similarity, and Fellegi-Sunter probabilistic linkage across candidate pairs.
7. **Privacy Mitigation**: Apply generalization and suppression transformations, then re-evaluate stages 4–6.
8. **Evaluation**: Evaluate linkage precision, recall, F1 score, and re-identification success rates against the isolated ground-truth boundary.
9. **Report Generation**: Compile all empirical metrics, formulas, assumptions, dataset parameters, and package versions into structured JSON and Markdown reports.

## Installation

Requirements: Python 3.11 or newer.

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Or install in editable mode with development dependencies:
pip install -e ".[dev]"
```

## Running the Pipeline

To execute the entire 9-stage pipeline from a configuration file and generate comprehensive audit reports:

```powershell
python -m shadowlink run-pipeline --config pipeline.json --out experiments/pipeline_run
```

Outputs will be saved to `experiments/pipeline_run/report.json` and `experiments/pipeline_run/report.md`.

## Interactive Demo Dashboard

Launch the self-contained, presentation-ready university project demo dashboard:

```powershell
# PowerShell launcher script
.\scripts\start_demo.ps1

# Or run directly via uvicorn:
uvicorn shadowlink.api.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/demo` in your browser.

The dashboard works completely offline (zero external scripts, zero CDNs, zero third-party assets) and provides 7 interactive tabs:
1. **Overview**: Pipeline stage progression and architecture flow.
2. **Data Generation**: Tunable synthetic generation parameters ($N$, noise, typos, missing rate).
3. **QI & k-Anonymity**: Candidate quasi-identifier detection and distribution analysis.
4. **Attacker Simulator**: Progressive disclosure auxiliary attribute narrowing curves ($|C| \to 1$).
5. **Linkage Engine**: Deterministic, similarity, and Fellegi-Sunter record linkage precision/recall/F1 benchmarking.
6. **Privacy Mitigation**: Generalization and suppression tradeoff analysis comparing privacy gain against discernibility loss.
7. **Report Tables**: Live-rendered benchmark Tables 5, 6, and 7.

To run automated smoke tests against the demo API:
```powershell
python scripts\demo_smoke.py
```

## Running Modular CLI Commands

Individual platform operations can be executed directly from the CLI:

```powershell
# 1. Generate synthetic bundle (A, B, C datasets + isolated ground truth)
python -m shadowlink generate --preset report_abc --n 500 --out-dir ./data/generated

# 2. Link Dataset A and Dataset B using similarity matching
python -m shadowlink link ./data/generated/A.csv ./data/generated/B.csv --attributes age,city --blocking-keys city --output ./data/generated/scored_pairs.csv

# 3. Simulate progressive attacker disclosure on a target record
python -m shadowlink attack ./data/generated/A.csv --target-id A-00001 --steps "age,city;course"

# 4. Evaluate linkage predictions against ground truth
python -m shadowlink evaluate ./data/generated/scored_pairs.csv ./data/generated/ground_truth.csv --left-dataset A --right-dataset B

# 5. Run reproducible benchmark experiment tables
python -m shadowlink experiment table5 --n 500 --seed 42 --format markdown
python -m shadowlink experiment table6 --n 500 --seed 42 --format markdown
python -m shadowlink experiment table7 --n 500 --seed 42 --format markdown
```

## Quality Gates & Verification

Run the full testing and quality assurance suite:

```powershell
# Gate 1: Full unit, API, and integration test suite
python -m pytest -q

# Gate 2: Strict coverage threshold (>= 90%)
python -m pytest --cov=shadowlink --cov-fail-under=90

# Gate 3: Ruff linting and formatting check
ruff check .

# Gate 4: Static type checking
mypy src

# Gate 5: Zero deprecations/warnings treated as errors
python -W error -m pytest -q
```

## Repository Structure

```text
src/shadowlink/
  common/          Exceptions, schema validation, string normalisation
  profiler/        Data profiling, distribution metrics, cardinality analysis
  qi_analyser/     Quasi-identifier candidates, schema overlap, equivalence classes
  risk/            Class risk, candidate risk, discernibility metric
  mitigation/      Generalization, binning, coarsening, suppression, tradeoff analysis
  generator/       Latent population model, noise infusion, multi-table generation
  linkage/         Preprocessing, string comparators, blocking, Fellegi-Sunter, clustering
  attacker/        Adversary models, progressive attribute disclosure simulation
  evaluator/       Ground-truth boundary verification, precision, recall, F1, calibration
  pipeline/        End-to-end 9-stage pipeline runner and orchestrator
  cli/             Typer CLI entrypoint and subcommands
  api/             FastAPI service layer, REST endpoints, and /demo presentation dashboard
tests/
  unit/            Unit tests with deterministic calculation oracles
  api/             REST API endpoint tests, pagination bounds, and path traversal security
  integration/     End-to-end pipeline and multi-module integration tests
  fixtures/        Minimal deterministic fixture datasets (tiny_people_a, tiny_people_b)
docs/
  architecture.md  System architecture, component contracts, and data flow
  FORMULAS.md      Mathematical definitions and privacy metrics (Part 1)
  FORMULAS_LINKAGE.md Record linkage comparators, Fellegi-Sunter, and blocking math
  RESULTS_PART2.md Experimental protocol and benchmark references
  decisions/       13 Architecture Decision Records (ADRs) documenting design rationales
  api_contracts/   Module boundary interface contracts
scripts/
  start_demo.ps1   PowerShell launcher for demo web interface
  demo_smoke.py    Automated verification of demo endpoints and ground-truth boundary
pipeline.json      Sample reproducible configuration file for end-to-end pipeline
pyproject.toml     Packaging specification, dependencies, and test tool configuration
requirements.txt   Pinned dependency requirements (UTF-8)
```

## Database Storage Note

Storage is tested on **SQLite** (default `sqlite:///./shadowlink.db`, or `sqlite:///:memory:` for tests). PostgreSQL via `SHADOWLINK_DATABASE_URL` is supported (install the optional extra: `pip install -e ".[postgres]"`) but **untested**.

## Ground-Truth Boundary & Safety Principles

1. **Isolation**: Ground-truth tables and `entity_id` values are strictly quarantined to the evaluator module (`src/shadowlink/evaluator/ground_truth.py`). They are never accessible to the profiler, QI analyser, linkage engine, attacker simulator, or REST/Demo API responses.
2. **Forbidden Column Names**: Any dataset containing direct identifier columns (`ground_truth`, `true_id`, `true_identity`, `identity_key`) is immediately rejected upon ingestion.
3. **No Network Calls**: All operations run locally; no external web queries, CDNs, or telemetry are ever initiated.

## Limitations

* **Synthetic Data Scope**: The platform is calibrated and evaluated exclusively on synthetic datasets generated from defined latent parameter distributions.
* **Generalizability**: The latent generative assumptions (e.g., specific demographic distributions, typographical error rates) do not directly transfer to real-world populations without domain-specific re-parameterization.
* **Worst-Case Attacker Assumption**: Mitigation evaluations assume a worst-case adversary who possesses perfect external knowledge of the target's unmitigated quasi-identifiers.
