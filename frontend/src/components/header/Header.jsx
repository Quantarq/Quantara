import React from 'react';
import { ReactComponent as Logo } from 'assets/images/logo.svg';
import { NavLink } from 'react-router-dom';
import TelegramLogin from '../Telegram/TelegramLogin';
import './header.css';

function Header({ walletId, onConnectWallet, onLogout, tgUser, setTgUser }) {
  return (
    <nav>
      <div className="list-items">
        <div className="logo">
          <NavLink to="/">
            <Logo />
          </NavLink>
        </div>
        <div className="nav-items">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active-link' : '')}>
            Home
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'active-link' : '')}>
            Dashboard
          </NavLink>
        </div>
        <div className="wallet-section">
          <TelegramLogin user={tgUser} onLogin={setTgUser} />
          {walletId ? (
            <div className="wallet-container">
              <button className="logout-button" onClick={onLogout}>
                Log out
              </button>
              <div className="wallet-id">{`${walletId.slice(0, 4)}...${walletId.slice(-4)}`}</div>
            </div>
          ) : (
            <button className="gradient-button" onClick={onConnectWallet}>
              <span>Connect Wallet</span>
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Header;
