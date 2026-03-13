import React from 'react';

const FooterAuth = () => (
    <footer style={{
        textAlign: 'center',
        padding: '1rem',
        background: '#f5f5f5',
        color: '#555',
        fontSize: '0.9rem'
    }}>
        &copy; {new Date().getFullYear()} Revmine. All rights reserved.
    </footer>
);

export default FooterAuth;
