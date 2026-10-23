import { configDefaults, defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // The owner asked to keep these disconnected legacy workflows as source.
    // Their historical tests depend on APIs and academic screens now removed.
    exclude: [
      ...configDefaults.exclude,
      'src/features/admin/dashboard/AdminDashboard.test.tsx',
      'src/features/admin/students/StudentImport.test.tsx',
      'src/features/admin/students/studentImport.test.ts',
      'src/features/admin/students/StudentManager.test.tsx',
      'src/features/faculty/dashboard/FacultyDashboard.test.tsx',
      'src/features/student/dashboard/StudentDashboard.test.tsx',
      'src/features/student/dashboard/StudentDashboardEdgeCases.test.tsx',
      'src/features/student/dashboard/StudentDashboardHardening.test.tsx',
      'src/features/student/dashboard/StudentDashboardIntegration.test.tsx',
      'src/features/student/dashboard/StudentDashboardStates.test.tsx',
      'src/features/students/StudentRegistrationInvitations.test.tsx',
      'src/features/students/StudentRegistrationWorkflow.test.tsx',
      'src/features/students/studentsNavigation.test.ts',
    ],
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
