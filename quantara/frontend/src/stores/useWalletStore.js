import { create } from 'zustand';
import axios from 'axios';

// Ensure axios sends cookies automatically with every request
axios.defaults.withCredentials = true;

export const useWalletStore = create((set) => ({
  walletId: null,
  isInitializing: true,

  setWalletId: (walletId) => set({ walletId }),

  /**
   * Initializes session status on application mount by checking cookie validity.
   * Completely bypasses local storage queries.
   */
  initializeSession: async () => {
    try {
      const response = await axios.get('/api/auth/session');
      if (response.data && response.data.walletId) {
        set({ walletId: response.data.walletId, isInitializing: false });
      }
    } catch (error) {
      // Session cookie is either missing, expired, or invalid
      set({ walletId: null, isInitializing: false });
    }
  },

  clearWallet: () => set({ walletId: null }),
}));