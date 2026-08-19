# Student Performance Prediction System

## Phase status
Phase 0 and Phase 1 are complete (DB models, Alembic migrations, synthetic data generator, DB seeding, CSV import). Do not introduce feature engineering, model training, API resources, or UI predictions until their respective phase is explicitly begun.

## Design rules
- Keep all academic rules in `backend/app/core/academic_config.py`.
- Keep runtime offline; do not add CDN or hosted-service dependencies.
- Prediction values must be produced by trained artifacts once prediction features are introduced.
- Do not use target-semester outcomes as model features.
