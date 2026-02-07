/**
 * E2E Tests: Authentication Flow
 * Tests the complete authentication user journey
 */

describe('Authentication Flow', () => {
  const timestamp = Date.now();
  const testEmail = `e2e-auth-${timestamp}@revmine.com`;
  const testPassword = 'TestPassword123!';

  beforeEach(() => {
    cy.visit('/');
  });

  describe('Registration', () => {
    it('should display registration form', () => {
      cy.visit('/register');
      cy.get('input[type="email"]').should('be.visible');
      cy.get('input[type="password"]').should('be.visible');
      cy.get('button[type="submit"]').should('be.visible');
    });

    it('should show validation errors for empty fields', () => {
      cy.visit('/register');
      cy.get('button[type="submit"]').click();
      // Expect validation message (implementation specific)
      cy.get('input[type="email"]:invalid').should('exist');
    });

    it('should show error for invalid email format', () => {
      cy.visit('/register');
      cy.get('input[type="email"]').type('invalid-email');
      cy.get('input[type="password"]').type(testPassword);
      cy.get('button[type="submit"]').click();
      cy.get('input[type="email"]:invalid').should('exist');
    });

    it('should successfully register a new user', () => {
      cy.visit('/register');
      cy.get('input[type="email"]').type(testEmail);
      cy.get('input[type="password"]').type(testPassword);
      
      // Fill optional fields if present
      cy.get('body').then(($body) => {
        if ($body.find('input[name="first_name"]').length > 0) {
          cy.get('input[name="first_name"]').type('E2E');
          cy.get('input[name="last_name"]').type('Tester');
        }
      });
      
      cy.get('button[type="submit"]').click();
      
      // Should redirect to login or workspace after registration
      cy.url().should('match', /\/(login|workspaces)/);
    });

    it('should show error for duplicate email registration', () => {
      // First register the user
      cy.registerUser({ email: `dup-${timestamp}@revmine.com`, password: testPassword });
      
      // Try to register again with same email
      cy.visit('/register');
      cy.get('input[type="email"]').type(`dup-${timestamp}@revmine.com`);
      cy.get('input[type="password"]').type(testPassword);
      cy.get('button[type="submit"]').click();
      
      // Should show error or stay on register page
      cy.url().should('include', '/register');
    });
  });

  describe('Login', () => {
    before(() => {
      // Ensure test user exists
      cy.registerUser({ email: testEmail, password: testPassword });
    });

    it('should display login form', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').should('be.visible');
      cy.get('input[type="password"]').should('be.visible');
      cy.get('button[type="submit"]').should('be.visible');
    });

    it('should show error for invalid credentials', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').type('wrong@email.com');
      cy.get('input[type="password"]').type('wrongpassword');
      cy.get('button[type="submit"]').click();
      
      // Should show error message or stay on login
      cy.url().should('include', '/login');
    });

    it('should successfully login with valid credentials', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testEmail);
      cy.get('input[type="password"]').type(testPassword);
      cy.get('button[type="submit"]').click();
      
      // Should redirect to workspaces
      cy.url().should('include', '/workspaces');
      
      // Token should be stored
      cy.window().its('localStorage.jwt').should('exist');
    });

    it('should persist authentication across page reload', () => {
      cy.loginViaUI(testEmail, testPassword);
      cy.reload();
      cy.url().should('include', '/workspaces');
    });
  });

  describe('Logout', () => {
    beforeEach(() => {
      cy.registerUser({ email: `logout-${timestamp}@revmine.com`, password: testPassword });
      cy.loginViaUI(`logout-${timestamp}@revmine.com`, testPassword);
    });

    it('should successfully logout', () => {
      // Find and click logout button (adjust selector as needed)
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="logout-btn"]').length > 0) {
          cy.get('[data-testid="logout-btn"]').click();
        } else if ($body.find('button:contains("Logout")').length > 0) {
          cy.contains('button', 'Logout').click();
        }
      });
      
      // Should redirect to login
      cy.url().should('include', '/login');
      
      // Tokens should be cleared
      cy.window().its('localStorage.jwt').should('not.exist');
    });
  });

  describe('Protected Routes', () => {
    it('should redirect to login when accessing protected route unauthenticated', () => {
      cy.logout();
      cy.visit('/workspaces');
      cy.url().should('include', '/login');
    });

    it('should allow access to protected route when authenticated', () => {
      cy.registerUser({ email: `protected-${timestamp}@revmine.com`, password: testPassword });
      cy.loginViaUI(`protected-${timestamp}@revmine.com`, testPassword);
      cy.visit('/workspaces');
      cy.url().should('include', '/workspaces');
    });
  });
});
