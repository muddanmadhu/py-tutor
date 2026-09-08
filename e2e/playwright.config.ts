import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end configuration.
 *
 * The suite runs against a stack that is already up (`make up`), because
 * bringing up Postgres, Redis, the API, the runner image and Vite from
 * Playwright's `webServer` hook is slower and hides failures. CI starts the
 * stack in a previous step; see `.github/workflows/ci.yml`.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // the suite shares one seeded database
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [['html'], ['github']] : [['list']],
  use: {
    baseURL: process.env.PYFORGE_WEB_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 20_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
