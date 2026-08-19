import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // No component tests exist yet (Phase 0 scaffold only); this keeps
    // `make test` green until Phase 6 adds React Testing Library + jsdom.
    passWithNoTests: true,
  },
})
