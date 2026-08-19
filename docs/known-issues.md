# Known issues (deferred)

Tracked here per user instruction so they aren't lost; to be addressed after
the last build phase rather than mid-build.

## Open

- **Frontend has no ESLint config.** `frontend/package.json` lists a bare
  `eslint` devDependency but no `eslint.config.js`, so `npm run lint` errors
  out immediately instead of running. The original Vite JS scaffold's
  `eslint.config.js` (root-level, using `@eslint/js`,
  `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`) was
  removed in the Phase 1 cleanup of the stray scaffold and never replaced
  with a TypeScript-aware equivalent. Needs `typescript-eslint`,
  `eslint-plugin-react-hooks`, and `eslint-plugin-react-refresh` added as
  devDependencies plus a `frontend/eslint.config.js` targeting
  `**/*.{ts,tsx}`.

- **`POST /predictions/batch` never populates `predicted_gpa`.** The
  `BatchPredictionRow` schema advertises a `predicted_gpa` field, but
  `predict_batch` in `app/api/v1/predictions.py` only ever calls
  `bulk_risk_scores` and builds every row with `predicted_gpa=None`; there is
  no GPA-regression path in the batch endpoint at all (unlike
  `POST /predictions/student/{id}`, which returns risk, GPA, and course-score
  predictions together). The frontend batch-upload results table renders this
  honestly as "—" rather than inventing a value. Fixing it means adding a GPA
  inference call inside `predict_batch`, mirroring `predict_student`.
- **Analytics spec wishlist not fully backed by the locked API contract.**
  Section I asks `/analytics` for a GPA histogram, an attendance-vs-performance
  scatter with a regression line, and a level comparison chart. Section H's
  locked endpoint list (`/analytics/overview`, `/trends`, `/correlations`,
  `/course-difficulty`) has no per-student/per-enrolment granular data to back
  these honestly — building them would mean either fetching full profiles for
  all ~1,200 students client-side (impractical against this backend) or adding
  new backend aggregation endpoints, which is beyond a frontend-only phase.
  Built instead: a session-trends line chart and course-difficulty bar chart,
  both backed by real existing endpoints. Flagged rather than faked.

## Fixed during Phase 6 (kept here as a record, no action needed)

- Lecturer dashboard's "Class risk" table rendered all scoped at-risk
  students unbounded (462 rows for the demo `lecturer01` account). Capped to
  10 rows with a "Showing N of total" note, matching the admin leaderboard
  pattern.
- Student dashboard treated a 404 from `POST /predictions/student/{id}`
  ("no ongoing enrolment to predict for") as a generic load error with a
  Retry button, which is misleading for a permanent condition. Now renders
  a proper empty state instead.
- The login page's demo student account (`mcm.20.00001@...`) had no ongoing
  enrolment, so the showcased student dashboard always hit the above error.
  Swapped to `eco.24.00002@...`, which has an active semester.
- Student dashboard's GPA/CGPA trend chart used `session` alone as the X-axis
  key; since two semesters share a session label, the line zigzagged.
  Switched to a combined `"{session} S{semester}"` label.
