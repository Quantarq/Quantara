import React from 'react';
import './telegramNotificationModal.css';
import useTelegramNotification from 'hooks/useTelegramNotification';
import { Notifier } from 'components/Notifier/Notifier';
import { useWalletStore } from 'stores/useWalletStore';


const TelegramNotificationModal = ({ onClose, telegramId }) => {
        const { walletId } = useWalletStore();

  const { subscribe, isLoading } = useTelegramNotification();

  const handleSubscribe = () => {
    subscribe({ telegramId, walletId });
  };

  return (
    <div className="notification-overlay">
      <Notifier />
      <div className="notification-backdrop" onClick={onClose} />
      <div className="notification-wrapper">
        <div className="notification-box">
          <div className="notification-content">
            <div className="notification-title">Telegram Notification</div>
            <h2>
              Do you want to enable telegram <br />
              notification bot?
            </h2>
            <p>
              This will allow you to receive quick notifications on your telegram line in realtime. You can disable this
              setting anytime.
            </p>
          </div>
          <div className="notification-actions">
            <button onClick={onClose} className="notification-btn notification-cancel-btn" disabled={isLoading}>
              Cancel
            </button>
            <button
              onClick={handleSubscribe}
              className="notification-btn notification-confirm-btn"
              disabled={isLoading}
            >
              {isLoading ? 'Subscribing...' : 'Yes, Sure'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TelegramNotificationModal;
