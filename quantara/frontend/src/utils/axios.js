import axios from 'axios';

export const axiosInstance = axios.create({
  baseURL: process.env.VITE_APP_BACKEND_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add response interceptor for centralized error handling
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(
        `API error ${error.response.status}:`,
        error.response.data?.detail || error.message
      );
    } else if (error.request) {
      console.error('Network error: no response received from server');
    } else {
      console.error('Request configuration error:', error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * Build the three auth headers required by protected API endpoints.
 *
 * Flow: GET /api/auth/nonce → sign nonce with Freighter → return headers.
 *
 * @param {string} walletId - The Stellar public key (G...)
 * @returns {Promise<{'x-wallet-id': string, 'x-nonce': string, 'x-signature': string}>}
 */
export const getAuthHeaders = async (walletId) => {
  const { signNonce } = await import('../services/wallet');
  const { data } = await axiosInstance.get('/api/auth/nonce', { params: { wallet_id: walletId } });
  const signature = await signNonce(data.nonce, walletId);
  return {
    'x-wallet-id': walletId,
    'x-nonce': data.nonce,
    'x-signature': signature,
  };
};
