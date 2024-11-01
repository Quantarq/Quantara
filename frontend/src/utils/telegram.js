import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const saveTelegramUser = async (telegramUser, walletId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/telegram/save-user`, {
      telegram_id: telegramUser.id,
      username: telegramUser.username,
      first_name: telegramUser.first_name,
      last_name: telegramUser.last_name,
      photo_url: telegramUser.photo_url,
      wallet_id: walletId
    });
    return response.data;
  } catch (error) {
    console.error('Error saving Telegram user:', error);
    throw error;
  }
};

export const getTelegramUserWalletId = async (tg_user) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/telegram/get-wallet-id/${tg_user.id}`, {
      raw: window.Telegram.initData || tg_user,
      is_webapp: !!window.Telegram.initData
    });
    return response.data.wallet_id;
  } catch (error) {
    console.error('Error getting wallet ID for Telegram user:', error);
    throw error;
  }
};