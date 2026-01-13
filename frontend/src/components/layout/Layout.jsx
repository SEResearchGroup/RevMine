import React from 'react';
import ThemeToggle from '../ui/ThemeToggle';

const Layout = ({ children }) => {
    return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
            <header style={{ background: '#222', color: '#fff', padding: '1rem' }}>
                <h1>My App</h1>
                <ThemeToggle />
            </header>
            <main style={{ flex: 1, padding: '2rem' }}>
                {children}
            </main>
            <footer style={{ background: '#222', color: '#fff', padding: '1rem', textAlign: 'center' }}>
                &copy; {new Date().getFullYear()} My App
            </footer>
        </div>
    );
};

export default Layout;