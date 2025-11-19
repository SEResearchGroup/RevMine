import React from 'react';

const NavbarAuth = () => {
    return (
        <nav style={{ padding: '1rem', background: '#f5f5f5', display: 'flex', justifyContent: 'space-between' }}>
            <div>
                <a href="/" style={{ textDecoration: 'none', color: '#333', fontWeight: 'bold' }}>MyApp</a>
            </div>
            <div>
                <a href="/login" style={{ marginRight: '1rem', textDecoration: 'none', color: '#333' }}>Login</a>
                <a href="/register" style={{ textDecoration: 'none', color: '#333' }}>Register</a>
            </div>
        </nav>
    );
};

export default NavbarAuth;