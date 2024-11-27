import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import './vaultLayout.css';

export function VaultLayout({ children }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-content">
          <h2 className="sidebar-title">Vault</h2>
          <nav className="sidebar-nav">
            <Link to="/vault" className="nav-item">
              <span className="nav-bullet">•</span>
              Home
            </Link>
            <Link to="/stake" className="nav-item">
              <span className="nav-bullet">•</span>
              Stake
            </Link>
            <Link to="/withdraw" className="nav-item">
              <span className="nav-bullet">•</span>
              Withdraw
            </Link>
          </nav>
        </div>
      </aside>

      <main className="main-content">
        {children}
        <Outlet />
      </main>
    </div>
  )
}
