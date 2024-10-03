import React from 'react';
import './header.css'
import { ReactComponent as Logo } from "../../assets/images/logo.svg";

function Header({ walletId, onConnectWallet, onLogout }) {
  return (
      <nav>
          <div className='list-items'>
              <div className='logo'>
                  <Logo/>
              </div>
              <div className='nav-items'>
                  <a href="#home">Home</a>
                  <a href="#about">Dashboard</a>
              </div>
              <div className='wallet-section'>
                  {walletId ? (
                      <div className='wallet-container'>
                          <div className='wallet-id'>
                              {`${walletId.slice(0, 4)}...${walletId.slice(-4)}`}
                          </div>
                          <button className='gradient-button'
                              onClick={onLogout}
                          >
                              Log Out
                          </button>
                      </div>
                  ) : (
                      <button className='gradient-button'
                          onClick={onConnectWallet}
                      >
                          <span>Connect Wallet</span>
                      </button>
                  )}
              </div>
          </div>
      </nav>
  );
}

export default Header;