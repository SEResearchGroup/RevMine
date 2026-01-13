import React from 'react';

const Dashboard = () => {
    return (
        <div style={{ padding: '2rem' }}>
            <h1>Dashboard</h1>
            <p>Welcome to your dashboard!</p>
            <div style={{ marginTop: '2rem', display: 'flex', gap: '2rem' }}>
                <div style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '8px', flex: 1 }}>
                    <h2>Stats</h2>
                    <p>Users: 120</p>
                    <p>Revenue: $2,400</p>
                </div>
                <div style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '8px', flex: 1 }}>
                    <h2>Recent Activity</h2>
                    <ul>
                        <li>User John signed up</li>
                        <li>Order #1234 completed</li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;