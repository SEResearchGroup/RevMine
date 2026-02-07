import '@testing-library/jest-dom';

// Mock localStorage
Object.defineProperty(global, 'localStorage', {
  value: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  },
  writable: true,
});

// Mock window.location
delete window.location;
window.location = { href: '', assign: jest.fn() };

// Suppress console errors in tests
global.console = {
  ...console,
  error: jest.fn(),
  warn: jest.fn(),
};
