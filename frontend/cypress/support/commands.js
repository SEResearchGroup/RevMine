// ***********************************************
// Custom Cypress Commands for RevMine E2E Testing
// ***********************************************

/**
 * Login command - authenticates user and stores tokens
 */
Cypress.Commands.add('login', (email, password) => {
  const userEmail = email || Cypress.env('TEST_USER_EMAIL');
  const userPassword = password || Cypress.env('TEST_USER_PASSWORD');

  cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL')}/auth/login`,
    body: {
      email: userEmail,
      password: userPassword,
    },
    failOnStatusCode: false,
  }).then((response) => {
    if (response.status === 200) {
      window.localStorage.setItem('jwt', response.body.access);
      window.localStorage.setItem('refresh_token', response.body.refresh);
    }
  });
});

/**
 * Login via UI - uses the login form
 */
Cypress.Commands.add('loginViaUI', (email, password) => {
  const userEmail = email || Cypress.env('TEST_USER_EMAIL');
  const userPassword = password || Cypress.env('TEST_USER_PASSWORD');

  cy.visit('/login');
  cy.get('input[type="email"]').type(userEmail);
  cy.get('input[type="password"]').type(userPassword);
  cy.get('button[type="submit"]').click();
  cy.url().should('include', '/workspaces');
});

/**
 * Register a new user via API
 */
Cypress.Commands.add('registerUser', (userData) => {
  const data = {
    email: userData.email || `test-${Date.now()}@revmine.com`,
    password: userData.password || 'TestPassword123!',
    first_name: userData.firstName || 'Test',
    last_name: userData.lastName || 'User',
    position: userData.position || 'Developer',
  };

  return cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL')}/auth/register`,
    body: data,
    failOnStatusCode: false,
  });
});

/**
 * Logout - clears tokens from localStorage
 */
Cypress.Commands.add('logout', () => {
  window.localStorage.removeItem('jwt');
  window.localStorage.removeItem('refresh_token');
});

/**
 * Create a workspace via API
 */
Cypress.Commands.add('createWorkspace', (workspaceData) => {
  const token = window.localStorage.getItem('jwt');
  
  return cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL')}/workspaces/`,
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: workspaceData,
    failOnStatusCode: false,
  });
});

/**
 * Delete a workspace via API
 */
Cypress.Commands.add('deleteWorkspace', (workspaceId) => {
  const token = window.localStorage.getItem('jwt');
  
  return cy.request({
    method: 'DELETE',
    url: `${Cypress.env('API_URL')}/workspaces/${workspaceId}/`,
    headers: {
      Authorization: `Bearer ${token}`,
    },
    failOnStatusCode: false,
  });
});

/**
 * Wait for API to be ready
 */
Cypress.Commands.add('waitForApi', () => {
  cy.request({
    method: 'GET',
    url: `${Cypress.env('API_URL')}/auth/`,
    failOnStatusCode: false,
    timeout: 30000,
  });
});

/**
 * Preserve auth tokens between tests
 */
Cypress.Commands.add('preserveAuth', () => {
  Cypress.Cookies.preserveOnce('jwt', 'refresh_token');
});

/**
 * Get by data-testid
 */
Cypress.Commands.add('getByTestId', (testId) => {
  return cy.get(`[data-testid="${testId}"]`);
});
