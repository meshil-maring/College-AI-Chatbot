import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Several accessibility-oriented form tests intentionally type through
    // every field. On constrained CI hosts, parallel jsdom workers can push a
    // correct user-event sequence past Vitest's 5s default and leave its
    // pending keystrokes to contaminate the next test. Keep the suite bounded
    // while allowing those real interaction paths to finish cleanly.
    testTimeout: 15_000,
  },
})
