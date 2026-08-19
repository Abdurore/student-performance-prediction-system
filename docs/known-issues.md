# Known issues (deferred)

Tracked here per user instruction so they aren't lost; to be addressed after
the last build phase rather than mid-build.

## Open

_Nothing currently open — see "Fixed during finalization" below._

## Fixed during finalization

- **Frontend now has a working ESLint config.** Added `typescript-eslint`,
  `eslint-plugin-react-hooks`, and `eslint-plugin-react-refresh` as
  devDependencies and a TypeScript-aware `frontend/eslint.config.js`
  targeting `**/*.{ts,tsx}` (the original Vite JS scaffold's config was
  removed in the Phase 1 cleanup and never replaced). Running `npm run lint`
  against the real codebase surfaced three genuine issues, all fixed rather
  than suppressed: `AuthContext`'s mount effect called `setIsLoading`
  synchronously for the no-token branch (restructured to a lazy `useState`
  initializer so the effect only runs for the async fetch path);
  `BatchUploadTab`'s mount effect had the same synchronous-setState pattern
  for pre-selected student IDs from the URL (replaced with lazy `useState`
  initializers, removing the effect and its `exhaustive-deps` disable
  comment entirely); and `Login`'s demo-account filler function was named
  `useDemoAccount`, which `react-hooks/rules-of-hooks` correctly flagged as
  an illegal hook call inside a click handler even though it isn't a hook
  (renamed to `fillDemoAccount`). Also split `AuthContext`'s context object
  into `hooks/useAuth.ts` to clear a `react-refresh/only-export-components`
  warning about mixing a context export with a component export in the same
  file. `npm run lint` now exits clean with zero errors and zero warnings.

- **`POST /predictions/batch` now populates `predicted_gpa`.** Added
  `prediction_service.bulk_gpa_scores`, mirroring `bulk_risk_scores`'s
  vectorized-predict-only pattern (no SHAP, since bulk scoring never carries
  a per-row explanation) rather than reimplementing GPA inference from
  scratch. `predict_batch` now persists a `GPA_REGRESSION` prediction
  alongside the existing `RISK_CLASSIFICATION` one for every row that
  succeeds. Verified with a test asserting the batch value matches
  `POST /predictions/student/{id}`'s GPA for the same student
  (`tests/test_predictions_api.py`), not just "is not null."

- **Analytics spec wishlist now backed by real endpoints.** Section I asks
  `/analytics` for a GPA histogram, an attendance-vs-performance scatter with
  a regression line, and a level comparison chart, but Section H's locked
  endpoint list (`/analytics/overview`, `/trends`, `/correlations`,
  `/course-difficulty`) had no per-student/per-enrolment granular data to
  back these honestly. Closed the gap with three new institution-wide,
  live-computed endpoints — `GET /analytics/gpa-distribution`,
  `GET /analytics/attendance-performance`, `GET /analytics/level-comparison`
  (see `docs/api.md`) — added as a documented amendment to Section H rather
  than scope creep, since the charts were in the original spec's intent. The
  frontend `/analytics` page now renders all three using the existing
  skeleton/empty/error state components. Verified with backend tests per
  endpoint (response shape plus one correctness check each, e.g. histogram
  bucket counts sum to the seeded student count) and by live browser
  verification against real seeded data.

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
