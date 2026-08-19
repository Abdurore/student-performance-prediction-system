# Student Performance Prediction System

Offline-first university project for early performance-risk prediction, GPA forecasting, and course-score forecasting. It uses a FastAPI backend, SQLite by default, and a React/Vite frontend.

## Current status

Phase 0 and Phase 1 are complete:

- Project scaffolding, central academic configuration, dependency manifests, and a FastAPI health endpoint (Phase 0).
- SQLModel tables for every entity in the data model, Alembic migrations, a causally-coherent synthetic data generator (1,200 students across 6 sessions), database seeding, and CSV import for real institutional data with row-level validation (Phase 1).

Feature engineering, model training, authentication, and dashboard features remain phase-gated.

Run `make seed` to (re)generate the synthetic dataset and load it into the database. It prints a calibration report and a verification report (correlation matrix, grade-classification distribution, missingness rates) so the seeded data's coherence can be checked without opening the database.

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

Every account `make seed` creates (one admin, 18 lecturers, 24 advisers, and one per student) shares the password `Demo@12345`. Admin login: `admin@university.edu.ng`. Student logins follow `<matric-no, lowercased, "/" -> ".">@university.edu.ng`, e.g. `csc.24.00001@university.edu.ng`. A real login flow is introduced in Phase 5.
