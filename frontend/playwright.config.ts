import { defineConfig, devices } from '@playwright/test';

// Tests run against the production build: the offline worker only exists there.
// Needs data in static/data/: the backend output (see README), or the test copy (`pnpm run test:data`).
export default defineConfig({
  testDir: 'tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:4173',
    serviceWorkers: 'allow',
    trace: 'retain-on-failure'
  },
  projects: [
    { name: 'unit', testMatch: /unit\/.*\.test\.ts/ },
    { name: 'e2e', testMatch: /e2e\/.*\.spec\.ts/, testIgnore: /offline\.spec\.ts/, use: { ...devices['Pixel 7'] } },
    // The offline tests measure real time (the saved forecast within 4 s). They run after the others,
    // on a quiet machine, so a busy CPU can't make them fail. `--project=timing` runs e2e first.
    { name: 'timing', testMatch: /e2e\/offline\.spec\.ts/, dependencies: ['e2e'], use: { ...devices['Pixel 7'] } }
  ],
  webServer: {
    command: 'pnpm run build && pnpm run preview --port 4173 --strictPort',
    url: 'http://localhost:4173',
    // Always a fresh server: `vite preview` indexes build/ when it starts, so one left running
    // from before a rebuild serves the page but 404s the new JavaScript.
    reuseExistingServer: false,
    timeout: 180_000
  }
});
