import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:5173",
    viewportWidth: 1280,
    viewportHeight: 720,
    video: false,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 30000,
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    env: {
      // Test credentials - these will be used for E2E testing
      TEST_USER_EMAIL: "e2e-test@revmine.com",
      TEST_USER_PASSWORD: "TestPassword123!",
      // GitHub token for testing collection flow - load from cypress.env.json (gitignored)
      // Create cypress.env.json with: {"GITHUB_TEST_TOKEN": "your_token_here"}
      API_URL: "http://localhost:8000/api/v1",
    },
  },
});
