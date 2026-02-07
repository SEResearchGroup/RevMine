// ***********************************************************
// Support file - loaded before each test file
// ***********************************************************

import './commands';

// Prevent uncaught exceptions from failing tests
Cypress.on('uncaught:exception', (err, runnable) => {
  // returning false here prevents Cypress from failing the test
  return false;
});

// Clear localStorage before each test
beforeEach(() => {
  cy.clearLocalStorage();
});
