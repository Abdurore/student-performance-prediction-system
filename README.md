# Student Performance Prediction System

Offline-first university project for early performance-risk prediction, GPA forecasting, and course-score forecasting. It uses a FastAPI backend, SQLite by default, and a React/Vite frontend.

## Current status

Phase 0 is complete: project scaffolding, central academic configuration, dependency manifests, and a FastAPI health endpoint are available. Database, ML, authentication, and dashboard features remain phase-gated.

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
