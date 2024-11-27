import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import './globals.css';
import Header from './components/header/Header';
import Dashboard from 'pages/spotnet/dashboard/Dashboard';
import Footer from './components/Footer/Footer';
import SpotnetApp from 'pages/spotnet/spotnet_app/SpotnetApp';
import Login from 'pages/Login';
import Form from 'pages/forms/Form';
import { createPortal } from 'react-dom';
import LogoutModal from './components/Logout/LogoutModal';
import { connectWallet, logout, checkForCRMToken } from 'services/wallet';
import { saveTelegramUser, getTelegramUserWalletId } from 'services/telegram';
import Documentation from 'pages/spotnet/documentation/Documentation';
import Withdraw from 'pages/vault/withdraw/Withdraw';
import { useWalletStore } from 'stores/useWalletStore';
function App() {
  const { walletId, setWalletId, removeWalletId } = useWalletStore();
  const [tgUser, setTgUser] = useState(JSON.parse(localStorage.getItem('tg_user')));
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (tgUser) {
      saveTelegramUser(tgUser, walletId)
        .then(() => console.log('Telegram user saved successfully'))
        .catch((error) => console.error('Error saving Telegram user:', error));
    }
  }, [walletId, tgUser]);

  useEffect(() => {
    if (!tgUser) {
      localStorage.removeItem('tg_user');
      return;
    }
    if (!walletId) {
      getTelegramUserWalletId(tgUser)
        .then((fetchedWalletId) => {
          if (fetchedWalletId) {
            setWalletId(fetchedWalletId);
          }
        })
        .catch((error) => console.error('Error fetching wallet ID:', error));
      localStorage.setItem('tg_user', JSON.stringify(tgUser));
    }
  }, [tgUser, walletId, setWalletId]);

  const handleConnectWallet = async () => {
    try {
      setError(null);
      const walletAddress = await connectWallet();

      if (!walletAddress) {
        throw new Error('Failed to connect wallet');
      }

      const hasCRMToken = await checkForCRMToken(walletAddress);
      if (!hasCRMToken) {
        return; 
      }

      setWalletId(walletAddress);
    } catch (err) {
      console.error('Failed to connect wallet:', err);
      setError(err.message);
    }
  };

  const handleLogout = () => {
    logout();
    removeWalletId();
    closeModal();
    navigate('/');
  };

  const handleLogoutModal = () => {
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
  };

  return (
    <div className="App">
      {showModal && createPortal(<LogoutModal onClose={closeModal} onLogout={handleLogout} />, document.body)}
      <Header
        tgUser={tgUser}
        setTgUser={setTgUser}
        onConnectWallet={handleConnectWallet}
        onLogout={handleLogoutModal}
      />
      <main>
        {error && <div className="alert alert-danger">{error}</div>}
        <Routes>
          <Route index element={<SpotnetApp onConnectWallet={handleConnectWallet} onLogout={handleLogout} />} />
          <Route
            path="/login"
            element={walletId ? <Navigate to="/" /> : <Login onConnectWallet={handleConnectWallet} />}
          />
          <Route path="/dashboard" element={<Dashboard telegramId={tgUser} />} />
          <Route path="/withdraw" element={<Withdraw />} />
          <Route path="/form" element={<Form />} />
          <Route path="/documentation" element={<Documentation />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
