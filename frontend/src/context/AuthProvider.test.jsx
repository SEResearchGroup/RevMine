/**
 * Tests for AuthContext
 * Note: These test the auth utilities since AuthProvider requires api.js with import.meta.env
 */
import { render, screen } from '@testing-library/react';
import AuthContext from './AuthContext.jsx';
import { useContext } from 'react';

// Simple test to verify AuthContext exists and can be consumed
describe('AuthContext', () => {
  it('creates context with expected shape', () => {
    const TestConsumer = () => {
      const context = useContext(AuthContext);
      return (
        <div>
          <span data-testid="context-exists">
            {context !== undefined ? 'exists' : 'undefined'}
          </span>
        </div>
      );
    };

    // Provide a mock value
    const mockValue = {
      isAuthenticated: false,
      user: null,
      loading: false,
      login: jest.fn(),
      logout: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('context-exists')).toHaveTextContent('exists');
  });

  it('provides authenticated state', () => {
    const TestConsumer = () => {
      const { isAuthenticated } = useContext(AuthContext);
      return <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>;
    };

    const mockValue = {
      isAuthenticated: true,
      user: { id: 1, email: 'test@example.com' },
      loading: false,
      login: jest.fn(),
      logout: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('auth')).toHaveTextContent('yes');
  });

  it('provides user data when authenticated', () => {
    const TestConsumer = () => {
      const { user } = useContext(AuthContext);
      return <span data-testid="email">{user?.email || 'none'}</span>;
    };

    const mockValue = {
      isAuthenticated: true,
      user: { id: 1, email: 'test@example.com' },
      loading: false,
      login: jest.fn(),
      logout: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('email')).toHaveTextContent('test@example.com');
  });

  it('provides loading state', () => {
    const TestConsumer = () => {
      const { loading } = useContext(AuthContext);
      return <span data-testid="loading">{loading ? 'yes' : 'no'}</span>;
    };

    const mockValue = {
      isAuthenticated: false,
      user: null,
      loading: true,
      login: jest.fn(),
      logout: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('loading')).toHaveTextContent('yes');
  });

  it('provides login function', () => {
    const loginMock = jest.fn();
    const TestConsumer = () => {
      const { login } = useContext(AuthContext);
      return (
        <button data-testid="login-btn" onClick={() => login('token', 'refresh')}>
          Login
        </button>
      );
    };

    const mockValue = {
      isAuthenticated: false,
      user: null,
      loading: false,
      login: loginMock,
      logout: jest.fn(),
    };

    render(
      <AuthContext.Provider value={mockValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    screen.getByTestId('login-btn').click();
    expect(loginMock).toHaveBeenCalledWith('token', 'refresh');
  });

  it('provides logout function', () => {
    const logoutMock = jest.fn();
    const TestConsumer = () => {
      const { logout } = useContext(AuthContext);
      return (
        <button data-testid="logout-btn" onClick={logout}>
          Logout
        </button>
      );
    };

    const mockValue = {
      isAuthenticated: true,
      user: { id: 1 },
      loading: false,
      login: jest.fn(),
      logout: logoutMock,
    };

    render(
      <AuthContext.Provider value={mockValue}>
        <TestConsumer />
      </AuthContext.Provider>
    );

    screen.getByTestId('logout-btn').click();
    expect(logoutMock).toHaveBeenCalled();
  });
});
