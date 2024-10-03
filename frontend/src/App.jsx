import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/header/Header';
import Footer from './components/Footer';
import SpotnetApp from './pages/spotnet/spotnet_app/SpotnetApp';
import Login from "./pages/Login";
import { connectWallet, logout } from './utils/wallet';
import Home from "./pages/spotnet/home/Home";

function App() {
  const [walletId, setWalletId] = useState(localStorage.getItem('wallet_id'));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (walletId) {
      localStorage.setItem('wallet_id', walletId);
    } else {
      localStorage.removeItem('wallet_id');
    }
  }, [walletId]);

  const handleConnectWallet = async () => {
    try {
      setError(null);
      const address = await connectWallet();
      if (address) {
        setWalletId(address);
      }
    } catch (err) {
      console.error("Failed to connect wallet:", err);
      setError(err.message);
    }
  };

  const handleLogout = () => {
    logout();
    setWalletId(null);
  };

  return (
    <Router>
      <div className="App">
        <Header walletId={walletId} onConnectWallet={handleConnectWallet} onLogout={handleLogout} />
        <Home walletId={walletId} onConnectWallet={handleConnectWallet} onLogout={handleLogout} />
        <main className="container" style={{ flex: 1 }}>
          {error && <div className="alert alert-danger">{error}</div>}
          <Routes>
            <Route index element={<SpotnetApp />} />
            <Route path="/login" element={walletId ? <Navigate to="/" /> : <Login onConnectWallet={handleConnectWallet} />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;
