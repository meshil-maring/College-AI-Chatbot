import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Bound parallel jsdom environments so async UI queries are not starved
    // by the default worker count on hosts exposing many logical CPUs.
    pool: 'vmThreads',
    maxWorkers: 2,
    // Several accessibility-oriented form tests intentionally type through
    // every field. On constrained CI hosts, parallel jsdom workers can push a
    // correct user-event sequence past Vitest's 5s default and leave its
    // pending keystrokes to contaminate the next test. Keep the suite bounded
    // while allowing those real interaction paths to finish cleanly.
    testTimeout: 15_000,
  },
})
