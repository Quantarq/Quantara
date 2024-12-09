import { axiosInstance } from '../utils/axios';

export const saveTelegramUser = async (telegramUser, walletId) => {
  try {
    const response = await axiosInstance.post(`/api/telegram/save-user`, {
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
    const response = await axiosInstance.post(`/api/telegram/get-wallet-id/${tg_user.id}`, {
      raw: window.Telegram.initData || tg_user,
      is_webapp: !!window.Telegram.initData
    });
    return response.data.wallet_id;
  } catch (error) {
    console.error('Error getting wallet ID for Telegram user:', error);
    throw error;
  }
};

export const subscribeToNotification = async (telegram_id, wallet_id) => {
  try {
    const response = await axiosInstance.post("/api/subscribe-to-notification", {
      telegram_id: telegram_id,
      wallet_id: wallet_id,
    });

    return response.data;
  } catch (error) {
    console.error("Error subscribing to notifications:", error);
    throw error;
  }
}

export const generateTelegramLink = async (wallet_id) => {
  try {
    const response = await axiosInstance.get(`/api/generate-telegram-link`, {
      params: { wallet_id: wallet_id },
    });
    return response.data;
  } catch (error) {
    console.error("Error generating Telegram link:", error);
    throw error;
  }
}