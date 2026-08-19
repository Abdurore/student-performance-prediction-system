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
