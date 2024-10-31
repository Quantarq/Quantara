import React from 'react';
import About from '../about/About';
import Partnership from '../partnership/Partnership';
import Information from '../information/Information';
import DontMiss from '../dont_miss/DontMiss';
import Home from '../home/Home';

const SpotnetApp = ({ walletId, onConnectWallet, onLogout }) => {
  return (
    <div className="spotnet-app">
      <Home walletId={walletId} onConnectWallet={onConnectWallet} onLogout={onLogout} />
      <About />
      <Partnership />
      <Information />
      <DontMiss walletId={walletId} onConnectWallet={onConnectWallet} onLogout={onLogout} />
    </div>
  );
};

export default SpotnetApp;
