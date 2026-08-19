# Student Performance Prediction System

Offline-first university project for early performance-risk prediction, GPA forecasting, and course-score forecasting. It uses a FastAPI backend, SQLite by default, and a React/Vite frontend.

## Current status

Phases 0-9 are complete:

- Project scaffolding, central academic configuration, dependency manifests, and a FastAPI health endpoint (Phase 0).
- SQLModel tables for every entity in the data model, Alembic migrations, a causally-coherent synthetic data generator (1,200 students across 6 sessions), database seeding, and CSV import for real institutional data with row-level validation (Phase 1).
- Feature engineering (35+ engineered features across academic history, current performance, attendance, engagement, load/context, and interactions), the data-leakage guard (`ml.features.assert_no_leakage`), and the shared preprocessing pipeline used by every model in Phase 3 (Phase 2).
- Training and comparison of six algorithms (logistic/linear regression, decision tree, random forest, XGBoost, SVM, MLP) across all three prediction tasks (risk classification, GPA regression, course-score regression), tuned via `GridSearchCV` over shared `StratifiedGroupKFold`/`GroupKFold` splits grouped by student, SMOTE compared with/without for classification, a temporal holdout (train on earlier sessions, test on the most recent), the 96%/0.95 leakage-warning threshold check, and persisted metrics JSON, 300dpi charts, and joblib artifacts mirrored into `model_registry` (Phase 3).
- Model-agnostic SHAP explainability (`ml.explain`) that explains every algorithm uniformly by wrapping each trained pipeline's own `predict`/`predict_proba` rather than special-casing tree/linear/kernel explainers; a natural-language template layer rendering the top 5 contributors per student as readable sentences (e.g. "Attendance rate of 41% is the largest factor, increasing risk by 23 percentage points."); global feature-importance charts per task; and a fairness audit (`ml.fairness`) across gender/entry_mode/accommodation on each task's temporal holdout, flagging any group disparity above 10 percentage points and mirroring the report into `model_registry.fairness_report` (Phase 4).
- A FastAPI backend (all endpoints under `/api/v1`, documented at `/docs`) with JWT auth and role-based access enforced as a shared dependency plus row-level scoping in the service layer (admin sees everything; a lecturer only students in courses they teach; an adviser only their assigned students; a student only themself, read-only). Every prediction endpoint serves real inference from the active trained artifacts -- never mocked -- including per-student SHAP explanations, with Section I's ethical constraint (a student's own explanation panel shows only actionable factors, in forward-looking language, never a bare "predicted to fail") enforced server-side. Also: student CRUD/CSV import, course/enrolment/attendance management with automatic grade recomputation, live analytics (dashboard overview, GPA trends, feature correlations, course difficulty), model registry/comparison/activation/retraining, intervention tracking, and PDF reports via reportlab (Phase 5).

- A React/TypeScript/Tailwind frontend (`frontend/`) served at `http://localhost:5173` in dev: JWT auth with visible demo credentials per role, a role-aware dashboard (institution overview for admins, class risk for lecturers, caseload-by-urgency for advisers, and an outlook with forward-looking, non-alarmist focus areas for students), a searchable/paginated student directory with on-demand predictions and PDF reports, intervention logging and status tracking, institution analytics (feature correlations, course difficulty), and admin model management (comparison, fairness audits, activation, retraining) (Phases 6-7).
- A `/predict` page (single-student search-and-predict, plus a batch CSV-upload tab with template download, client-side validation, and a results table against `POST /predictions/batch`), bulk-select-to-predict on the student directory, session-trend and course-difficulty charts on the analytics page, and per-model diagnostics on the models page -- confusion matrix, ROC curve, and calibration curve for classification; predicted-vs-actual and residual scatter for regression -- all from real persisted metrics (Phase 8).

- Full documentation set: `docs/architecture.md` (tech stack, ERD, prediction data-flow, use-case diagram, design decisions), `docs/api.md` (every endpoint with its role requirement), `docs/user-manual.md` (per-role screen-by-screen guide), `docs/installation.md` (clean-machine setup + troubleshooting), `docs/demo-script.md` (timed 8-minute walkthrough + 12 examiner questions). A measured backend+frontend test suite: 132 backend tests (87% coverage across `app/services/` + `ml/`), 35 frontend tests (vitest + React Testing Library) covering the CSV batch-upload parser, the typed API client's error handling, auth/role route-guarding, and the login page's demo-credential flow (Phase 9).

A subsequent finalization pass closed every item that was open at the end of Phase 9: `predict_batch` now computes real `predicted_gpa` via `bulk_gpa_scores`; three new live-computed analytics endpoints (`gpa-distribution`, `attendance-performance`, `level-comparison`) back the charts the spec's analytics wish list named, wired into the `/analytics` page; and the frontend has a working `eslint.config.js` (`typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`) with `npm run lint` clean. See `docs/known-issues.md` for the full record — nothing is currently open.

Run `make seed` to (re)generate the synthetic dataset and load it into the database. It prints a calibration report and a verification report (correlation matrix, grade-classification distribution, missingness rates) so the seeded data's coherence can be checked without opening the database.

Run `make train` to train and compare all six algorithms across all three tasks. It prints a comparison table per task and writes metrics JSON to `backend/ml/artifacts/metrics/`, model artifacts to `backend/ml/artifacts/models/`, and 300dpi charts to `docs/diagrams/`.

After training, `python -m ml.explain` writes global feature-importance JSON/charts and `python -m ml.fairness` writes the fairness audit JSON, both under `backend/ml/artifacts/`. `ml.explain.explain_student(student_id, task)` and `ml.explain.explain_enrolment(student_id, course_id)` return per-student/per-enrolment top-5 explanations as readable sentences for any valid ID.

Run `make dev` (after `make seed` and `make train`) to start the API at `http://127.0.0.1:8000`; interactive docs are at `http://127.0.0.1:8000/docs`. Log in via `POST /api/v1/auth/login` with any seeded demo account (see below) to get a bearer token for the other endpoints.

## Prerequisites

- Python 3.11
- Node.js 20 or newer
- GNU Make is optional; Windows users can use the Python command directly.

## Local setup

```bash
python scripts/commands.py install
python scripts/commands.py dev
```

Or, on systems with Make:

```bash
make install
make dev
```

The API health check is at `http://127.0.0.1:8000/health`.

## Configuration

Copy `.env.example` to `.env` before customising local settings. Academic scales, assessment weights, grade bands, and standing thresholds are centralized in `backend/app/core/academic_config.py`.

## Seeded demo accounts

Every account `make seed` creates (one admin, 18 lecturers, 24 advisers, and one per student) shares the password `Demo@12345`. Admin login: `admin@university.edu.ng`. Student logins follow `<matric-no, lowercased, "/" -> ".">@university.edu.ng`, e.g. `csc.24.00001@university.edu.ng`.
