# Student Performance Prediction System

## Phase status
Phases 0-7 are complete (DB models/migrations, synthetic data generator/seeding/CSV import, feature engineering + leakage guard + preprocessing, training all six algorithms x three tasks with tuning/metrics/artefacts, SHAP explainability + natural-language layer + fairness audit, FastAPI backend with JWT auth/role permissions/all endpoints serving real predictions, and a React/TypeScript frontend covering auth, role-aware dashboards, students, interventions, analytics, and model administration). See `docs/known-issues.md` for deferred cleanup items.

## Design rules
- Keep all academic rules in `backend/app/core/academic_config.py`.
- Keep runtime offline; do not add CDN or hosted-service dependencies.
- Prediction values must be produced by trained artifacts once prediction features are introduced.
- Do not use target-semester outcomes as model features.
