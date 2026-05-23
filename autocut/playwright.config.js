import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "chrome",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm start",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
  projects: [
    {
      name: "chrome",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
