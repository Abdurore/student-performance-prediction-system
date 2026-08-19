# Student Performance Prediction System

## Phase status
Phases 0-3 are complete (DB models/migrations, synthetic data generator/seeding/CSV import, feature engineering + leakage guard + preprocessing, training all six algorithms x three tasks with tuning/metrics/artefacts). Do not introduce SHAP explainability, the natural-language layer, fairness audit, API resources, or UI predictions until their respective phase is explicitly begun.

## Design rules
- Keep all academic rules in `backend/app/core/academic_config.py`.
- Keep runtime offline; do not add CDN or hosted-service dependencies.
- Prediction values must be produced by trained artifacts once prediction features are introduced.
- Do not use target-semester outcomes as model features.
