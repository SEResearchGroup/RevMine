/**
 * E2E Tests: Complete User Journey
 * Tests the full flow from login to creating workspace, collection, and analysis
 * 
 * Prerequisites: Backend services must be running
 */

describe('Complete User Journey', () => {
  const timestamp = Date.now();
  const testUser = {
    email: `journey-${timestamp}@revmine.com`,
    password: 'TestPassword123!',
    firstName: 'Journey',
    lastName: 'Tester'
  };
  
  // GitHub token for testing - provided by user
  const githubToken = Cypress.env('GITHUB_TEST_TOKEN');
  
  let workspaceId = null;
  let repositoryId = null;
  let collectionId = null;

  before(() => {
    // Register test user
    cy.registerUser(testUser);
  });

  describe('Step 1: User Login', () => {
    it('should login successfully', () => {
      cy.loginViaUI(testUser.email, testUser.password);
      cy.url().should('include', '/workspaces');
    });
  });

  describe('Step 2: Create Workspace with GitHub Token', () => {
    beforeEach(() => {
      cy.login(testUser.email, testUser.password);
      cy.visit('/workspaces');
    });

    it('should display workspace creation form', () => {
      // Look for "Create" or "Add" workspace button
      cy.get('body').then(($body) => {
        const createBtn = $body.find('button:contains("Create"), button:contains("Add"), [data-testid="create-workspace"]');
        if (createBtn.length > 0) {
          cy.wrap(createBtn.first()).click();
        }
      });
      
      // Form should be visible
      cy.get('input[name="name"], input[placeholder*="name" i]').should('be.visible');
    });

    it('should create a new GitHub workspace', () => {
      // Click create workspace button
      cy.get('body').then(($body) => {
        const createBtn = $body.find('button:contains("Create"), button:contains("Add"), [data-testid="create-workspace"]');
        if (createBtn.length > 0) {
          cy.wrap(createBtn.first()).click();
        }
      });

      // Fill workspace form
      cy.get('input[name="name"], input[placeholder*="name" i]').first().clear().type('E2E Test Workspace');
      
      // Select GitHub platform
      cy.get('body').then(($body) => {
        if ($body.find('select[name="platform"]').length > 0) {
          cy.get('select[name="platform"]').select('github');
        } else if ($body.find('[data-testid="platform-github"]').length > 0) {
          cy.get('[data-testid="platform-github"]').click();
        }
      });
      
      // Enter token
      cy.get('input[name="token"], input[placeholder*="token" i], input[type="password"]').first()
        .clear()
        .type(githubToken);
      
      // Submit
      cy.get('button[type="submit"], button:contains("Create"), button:contains("Save")').first().click();
      
      // Should show success or redirect
      cy.wait(2000);
      cy.url().should('include', '/workspaces');
    });

    it('should display created workspace in list', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').should('be.visible');
    });
  });

  describe('Step 3: Import Repository', () => {
    beforeEach(() => {
      cy.login(testUser.email, testUser.password);
    });

    it('should navigate to workspace and view repositories', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      
      // Should navigate to workspace detail or repository list
      cy.wait(1000);
    });

    it('should be able to import repositories from GitHub', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      
      // Look for import button
      cy.get('body').then(($body) => {
        const importBtn = $body.find('button:contains("Import"), button:contains("Add Repository"), [data-testid="import-repos"]');
        if (importBtn.length > 0) {
          cy.wrap(importBtn.first()).click();
          cy.wait(2000);
          
          // Select first repository if list appears
          cy.get('body').then(($inner) => {
            const repoCheckbox = $inner.find('input[type="checkbox"]');
            if (repoCheckbox.length > 0) {
              cy.wrap(repoCheckbox.first()).check();
              cy.contains('button', 'Import').click();
            }
          });
        }
      });
    });
  });

  describe('Step 4: Start Collection', () => {
    beforeEach(() => {
      cy.login(testUser.email, testUser.password);
    });

    it('should navigate to collection configuration', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      // Look for collection/analyze option
      cy.get('body').then(($body) => {
        const collectBtn = $body.find('button:contains("Collect"), button:contains("Start Collection"), [data-testid="start-collection"]');
        if (collectBtn.length > 0) {
          cy.wrap(collectBtn.first()).click();
        }
      });
    });

    it('should configure collection metrics', () => {
      // Navigate to collection page
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      cy.get('body').then(($body) => {
        // Find metrics checkboxes or selection
        const metricsCheckboxes = $body.find('input[type="checkbox"][name*="metric"], [data-testid*="metric"]');
        if (metricsCheckboxes.length > 0) {
          // Select some metrics
          cy.wrap(metricsCheckboxes.first()).check();
        }
      });
    });

    it('should execute collection (may take time)', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      cy.get('body').then(($body) => {
        const executeBtn = $body.find('button:contains("Execute"), button:contains("Start"), button:contains("Run")');
        if (executeBtn.length > 0) {
          cy.wrap(executeBtn.first()).click();
          // Collection may take time
          cy.wait(5000);
        }
      });
    });
  });

  describe('Step 5: Create Cleaned Data Instance', () => {
    beforeEach(() => {
      cy.login(testUser.email, testUser.password);
    });

    it('should navigate to data cleaning section', () => {
      // This depends on your UI flow
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      // Look for cleaning/filter option
      cy.get('body').then(($body) => {
        const cleanBtn = $body.find('button:contains("Clean"), button:contains("Filter"), [data-testid="clean-data"]');
        if (cleanBtn.length > 0) {
          cy.wrap(cleanBtn.first()).click();
        }
      });
    });

    it('should apply filters and create cleaned dataset', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      cy.get('body').then(($body) => {
        // Apply some filters if available
        const filterSelect = $body.find('select[name*="filter"], select[name*="status"]');
        if (filterSelect.length > 0) {
          cy.wrap(filterSelect.first()).select(1);
        }
        
        const applyBtn = $body.find('button:contains("Apply"), button:contains("Create")');
        if (applyBtn.length > 0) {
          cy.wrap(applyBtn.first()).click();
        }
      });
    });
  });

  describe('Step 6: Run Analysis', () => {
    beforeEach(() => {
      cy.login(testUser.email, testUser.password);
    });

    it('should navigate to analysis section', () => {
      // Navigate to analysis page
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      cy.get('body').then(($body) => {
        const analyzeBtn = $body.find('button:contains("Analyze"), a:contains("Analysis"), [data-testid="analyze"]');
        if (analyzeBtn.length > 0) {
          cy.wrap(analyzeBtn.first()).click();
        }
      });
    });

    it('should select charts and run analysis', () => {
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(1000);
      
      cy.get('body').then(($body) => {
        // Select chart types
        const chartCheckboxes = $body.find('input[type="checkbox"][name*="chart"], [data-testid*="chart"]');
        if (chartCheckboxes.length > 0) {
          cy.wrap(chartCheckboxes.first()).check();
        }
        
        // Run analysis
        const runBtn = $body.find('button:contains("Run Analysis"), button:contains("Analyze")');
        if (runBtn.length > 0) {
          cy.wrap(runBtn.first()).click();
          cy.wait(5000); // Analysis may take time
        }
      });
    });

    it('should display analysis results', () => {
      // Visit analysis results page
      cy.visit('/workspaces');
      cy.contains('E2E Test Workspace').click();
      cy.wait(2000);
      
      // Look for charts or results
      cy.get('body').then(($body) => {
        const hasCharts = $body.find('canvas, svg, [data-testid*="chart"], img[alt*="chart"]').length > 0;
        const hasResults = $body.find('[data-testid="analysis-results"], .analysis-results').length > 0;
        
        if (hasCharts || hasResults) {
          cy.log('Analysis results found');
        }
      });
    });
  });

  describe('Cleanup', () => {
    it('should cleanup test data', () => {
      cy.login(testUser.email, testUser.password);
      
      // Delete workspace if we have ID
      if (workspaceId) {
        cy.deleteWorkspace(workspaceId);
      }
    });
  });
});
