import React, { useState, useRef } from 'react';
import { ReactComponent as Logo } from 'assets/images/logo.svg';
import { ReactComponent as Menu } from 'assets/icons/menu.svg';
import { ReactComponent as Close } from 'assets/icons/close.svg';
import { NavLink } from 'react-router-dom';
import TelegramLogin from '../Telegram/TelegramLogin';
import { useClickOutside } from 'hooks/useClickOutside';
import './header.css';

function Header({ walletId, onConnectWallet, onLogout, tgUser, setTgUser }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const buttonRef = useRef(null);

  useClickOutside([menuRef, buttonRef], () => {
    setIsMenuOpen(false);
  });

  const toggleMenu = () => {
    setIsMenuOpen((prevState) => !prevState);
  };

  return (
    <nav>
      <div className="list-items">
        <div className="logo">
          <NavLink to="/">
            <Logo className='logo-icon'/>
          </NavLink>
        </div>
        <div className={`nav-items ${isMenuOpen ? 'open' : ''}`} ref={menuRef}>
          <NavLink
            to="/"
            end
            className={`link ${({ isActive }) => (isActive ? 'active-link' : '')}`}
            onClick={() => setIsMenuOpen(false)}
          >
            Home
          </NavLink>
          <NavLink
            to="/dashboard"
            className={`link ${({ isActive }) => (isActive ? 'active-link' : '')}`}
            onClick={() => setIsMenuOpen(false)}
            style={{fontSize:"1rem"}}
          >
            Dashboard
          </NavLink>
          <div className="wallet-section">
            <TelegramLogin user={tgUser} onLogin={setTgUser} />
            {walletId ? (
              <div className="wallet-container">
                <button className="logout-button"  onClick={onLogout}>
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
        <button
          className="hamburger-button"
          onClick={toggleMenu}
          aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
          ref={buttonRef}
        >
          {isMenuOpen ? <Close className="menu-icon" /> : <Menu className="menu-icon" />}
        </button>
      </div>
    </nav>
  );
}

export default Header;