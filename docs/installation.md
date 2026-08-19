# Installation

The whole system runs on a single machine with no internet access at
runtime (Section C). This guide takes a clean clone to a running, seeded,
trained instance.

## Prerequisites

- **Python 3.11**
- **Node.js 20 or newer**
- **GNU Make** is optional — every `make <target>` below has an equivalent
  `python scripts/commands.py <target>` that works identically on Windows,
  macOS, and Linux. Use whichever you have.

No Docker, no external database server, and no API keys are required. The
default database is a single SQLite file created on first `seed` run.

## 1. Clone and install dependencies

```bash
git clone <repository-url>
cd student-performance-prediction-system
make install
# or: python scripts/commands.py install
```

This creates a Python virtual environment at `.venv/`, installs
`backend/requirements.txt` into it, and runs `npm install` in `frontend/`.
Total install footprint is under 2GB (no TensorFlow/PyTorch — the ML stack
is scikit-learn, XGBoost, and SHAP only).

## 2. Configure environment variables (optional)

The defaults work out of the box for local development. To customise
anything (database URL, JWT secret, token lifetime, CORS origin), copy the
example file into the **backend's** working directory — settings are loaded
relative to where the backend process runs, which is `backend/`:

```bash
cp .env.example backend/.env
```

Then edit `backend/.env`. Relevant keys: `DATABASE_URL` (swap to
`postgresql://...` to use Postgres instead of SQLite — nothing else in the
codebase changes), `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
`CORS_ORIGINS`.

For the frontend, `frontend/.env.example` sets `VITE_API_BASE_URL` to
`http://127.0.0.1:8000/api/v1`, matching the backend's default host/port. It
only needs overriding if you change the backend's port.

## 3. Generate the seed dataset

```bash
make seed
# or: python scripts/commands.py seed
```

This applies Alembic migrations, then runs the synthetic data generator
(1,200 students across 6 sessions with causally-coherent correlations —
see `docs/architecture.md` §6) and loads it into the database, then prints a
verification report (correlation matrix, grade-distribution check,
missingness rates) so you can confirm the seeded data looks right without
opening the database yourself.

To load real institutional data instead, see `backend/app/db/csv_import.py`
— it validates against the same schema and produces a row-level error
report; no code changes are needed to use real data (Section F).

## 4. Train the models

```bash
make train
# or: python scripts/commands.py train
```

Trains and compares all six algorithms (logistic/linear regression,
decision tree, random forest, XGBoost, SVM, MLP) across all three
prediction tasks, via `GridSearchCV` over grouped cross-validation splits.
This takes several minutes — it's real hyperparameter search, not a
placeholder fit. It prints a comparison table per task, writes metrics JSON
to `backend/ml/artifacts/metrics/`, model artifacts to
`backend/ml/artifacts/models/`, and 300dpi charts to `docs/diagrams/`.

After training, two more commands populate explainability and fairness
artifacts (also required before the frontend's Models page has anything to
show):

```bash
cd backend
../.venv/bin/python -m ml.explain
../.venv/bin/python -m ml.fairness
```

(On Windows: `..\.venv\Scripts\python -m ml.explain`, etc.)

## 5. Start the app

```bash
make dev
# or: python scripts/commands.py dev
```

Starts the backend at `http://127.0.0.1:8000` (interactive API docs at
`http://127.0.0.1:8000/docs`) and the frontend dev server at
`http://localhost:5173`, concurrently. Open the frontend URL and log in
with any seeded demo account — see `docs/user-manual.md` for the full list;
the login page also displays them directly.

## One-shot: everything above in one command

```bash
make demo
# or: python scripts/commands.py demo
```

Runs install → seed → train → dev in sequence. This is the command a
clean-machine, offline verification should use.

## Running tests

```bash
make test
# or: python scripts/commands.py test
```

Runs the backend pytest suite (`backend/tests/`) and the frontend vitest
suite (`frontend/src/**/*.test.{ts,tsx}`). To see backend coverage broken
down by module:

```bash
cd backend
../.venv/bin/python -m pytest tests -q --cov=app --cov=ml --cov-report=term-missing
```

## Troubleshooting

- **Port already in use.** Something else is bound to 8000 or 5173. Stop
  it, or run `uvicorn app.main:app --port <other>` /
  `npm run dev -- --port <other>` directly and update
  `frontend/.env`'s `VITE_API_BASE_URL` to match.
- **"No active model registered for task '...'. Run `make train` first."**
  You started the backend before running `make train`, or a task's model
  was never activated. Run `make train`, then confirm via `GET /models`
  that each task has exactly one `is_active: true` row.
- **Frontend requests fail with a CORS error in the browser console.** The
  frontend origin doesn't match `CORS_ORIGINS` in `backend/.env` (or the
  default `http://localhost:5173`). Note `localhost` and `127.0.0.1` are
  different origins to a browser — use whichever `backend/.env`'s
  `CORS_ORIGINS` actually lists.
- **A single prediction feels slow (several seconds).** This is expected
  under `uvicorn`'s single-worker dev server: each prediction call loads a
  `.joblib` pipeline and runs a real SHAP explanation, and concurrent
  requests queue rather than truly parallelising. It is not a hung request.
- **`make train` reports a leakage warning and halts.** By design (Section
  G) — if any model's accuracy exceeds 96% or R² exceeds 0.95, the pipeline
  assumes a target-semester column leaked into the features and refuses to
  report the (likely meaningless) score. Check recent changes to
  `ml/features.py` or `ml/config.py`'s leakage-guard lists before
  re-running.
