import React from 'react';

const sidebarItems = [
    { name: 'Home', link: '/' },
    { name: 'Dashboard', link: '/dashboard' },
    { name: 'Settings', link: '/settings' },
];

const Sidebar = () => (
    <div style={{
        width: '200px',
        height: '100vh',
        background: '#222',
        color: '#fff',
        padding: '20px',
        boxSizing: 'border-box'
    }}>
        <h2 style={{ marginBottom: '30px' }}>Sidebar</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
            {sidebarItems.map(item => (
                <li key={item.name} style={{ marginBottom: '20px' }}>
                    <a href={item.link} style={{ color: '#fff', textDecoration: 'none' }}>
                        {item.name}
                    </a>
                </li>
            ))}
        </ul>
    </div>
);

export default Sidebar;