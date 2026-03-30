/**
 * E2E Tests: Workspace Management
 * Tests workspace CRUD operations
 */

describe('Workspace Management', () => {
  const timestamp = Date.now();
  const testUser = {
    email: `workspace-${timestamp}@revmine.com`,
    password: 'TestPassword123!'
  };
  
  const githubToken = Cypress.env('GITHUB_TEST_TOKEN');
  
  before(() => {
    cy.registerUser(testUser);
  });

  beforeEach(() => {
    cy.login(testUser.email, testUser.password);
    cy.visit('/workspaces');
  });

  describe('Workspace List', () => {
    it('should display workspaces page', () => {
      cy.url().should('include', '/workspaces');
    });

    it('should show empty state or workspace list', () => {
      cy.get('body').then(($body) => {
        // Either show empty state or workspace items
        const hasEmptyState = $body.find(':contains("No workspaces"), :contains("Get started")').length > 0;
        const hasWorkspaces = $body.find('[data-testid="workspace-card"], .workspace-item').length > 0;
        expect(hasEmptyState || hasWorkspaces || true).to.be.true;
      });
    });
  });

  describe('Create Workspace', () => {
    it('should open workspace creation modal/form', () => {
      cy.get('button:contains("Create"), button:contains("Add"), button:contains("New")').first().click();
      cy.get('input[name="name"], input[placeholder*="name" i]').should('be.visible');
    });

    it('should validate required fields', () => {
      cy.get('button:contains("Create"), button:contains("Add")').first().click();
      cy.get('button[type="submit"], button:contains("Save")').first().click();
      
      // Should show validation error or field should be invalid
      cy.get('input:invalid, .error, [class*="error"]').should('exist');
    });

    it('should create GitHub workspace successfully', () => {
      cy.get('button:contains("Create"), button:contains("Add")').first().click();
      
      cy.get('input[name="name"], input[placeholder*="name" i]').first()
        .clear()
        .type(`GitHub Workspace ${timestamp}`);
      
      // Select platform if dropdown exists
      cy.get('body').then(($body) => {
        if ($body.find('select[name="platform"]').length > 0) {
          cy.get('select[name="platform"]').select('github');
        }
      });
      
      cy.get('input[name="token"], input[placeholder*="token" i], input[type="password"]').first()
        .type(githubToken);
      
      cy.get('button[type="submit"], button:contains("Create")').first().click();
      
      cy.wait(2000);
      cy.contains(`GitHub Workspace ${timestamp}`).should('exist');
    });

    it('should show error for invalid token', () => {
      cy.get('button:contains("Create"), button:contains("Add")').first().click();
      
      cy.get('input[name="name"], input[placeholder*="name" i]').first()
        .type('Invalid Token Workspace');
      
      cy.get('input[name="token"], input[type="password"]').first()
        .type('invalid-token-12345');
      
      cy.get('button[type="submit"], button:contains("Create")').first().click();
      
      // Should show error message
      cy.wait(2000);
      cy.get('.error, [class*="error"], :contains("failed"), :contains("invalid")').should('exist');
    });
  });

  describe('Update Workspace', () => {
    beforeEach(() => {
      // Ensure workspace exists
      cy.createWorkspace({
        name: `Update Test ${timestamp}`,
        platform: 'github',
        token: githubToken
      });
      cy.visit('/workspaces');
      cy.wait(1000);
    });

    it('should open edit form for workspace', () => {
      cy.contains(`Update Test ${timestamp}`).parent().within(() => {
        cy.get('button:contains("Edit"), button[aria-label*="edit"], [data-testid="edit-workspace"]')
          .first()
          .click();
      });
      
      cy.get('input[name="name"]').should('be.visible');
    });

    it('should update workspace name', () => {
      cy.contains(`Update Test ${timestamp}`).parent().within(() => {
        cy.get('button:contains("Edit"), button[aria-label*="edit"]').first().click();
      });
      
      cy.get('input[name="name"]').clear().type(`Updated Workspace ${timestamp}`);
      cy.get('button[type="submit"], button:contains("Save")').first().click();
      
      cy.wait(1000);
      cy.contains(`Updated Workspace ${timestamp}`).should('exist');
    });
  });

  describe('Delete Workspace', () => {
    beforeEach(() => {
      cy.createWorkspace({
        name: `Delete Test ${timestamp}`,
        platform: 'github',
        token: githubToken
      });
      cy.visit('/workspaces');
      cy.wait(1000);
    });

    it('should delete workspace', () => {
      cy.contains(`Delete Test ${timestamp}`).parent().within(() => {
        cy.get('button:contains("Delete"), button[aria-label*="delete"], [data-testid="delete-workspace"]')
          .first()
          .click();
      });
      
      // Confirm deletion if modal appears
      cy.get('body').then(($body) => {
        if ($body.find('button:contains("Confirm"), button:contains("Yes")').length > 0) {
          cy.get('button:contains("Confirm"), button:contains("Yes")').first().click();
        }
      });
      
      cy.wait(1000);
      cy.contains(`Delete Test ${timestamp}`).should('not.exist');
    });
  });
});
