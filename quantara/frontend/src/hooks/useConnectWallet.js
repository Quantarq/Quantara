import { useMutation } from '@tanstack/react-query';
import { notify } from '../components/layout/notifier/Notifier';
import { connectWallet } from '../services/wallet';
import { startWalletConnectTransaction } from '../services/telemetry';

/**
 * Hook for connecting to the Freighter Stellar wallet.
 *
 * Wraps the underlying mutation in a Sentry transaction tagged `source:
 * "freighter"` so that wallet connection timings appear alongside
 * web-vitals in the Performance tab (Issue #277 acceptance criterion).
 *
 * @param {Function} setWalletId - Zustand store setter for wallet ID
 * @returns {useMutation} React Query mutation for wallet connection
 */
export const useConnectWallet = (setWalletId) => {
  return useMutation({
    mutationFn: async () => {
      const transaction = startWalletConnectTransaction('freighter');
      try {
        const publicKey = await connectWallet();
        transaction.setStatus('ok');
        if (!publicKey) throw new Error('Failed to connect wallet');
        return publicKey;
      } catch (err) {
        transaction.setStatus('internal_error');
        throw err;
      } finally {
        transaction.finish();
      }
    },
    onSuccess: (publicKey) => {
      localStorage.setItem('quantara_last_connected_wallet', publicKey);
      setWalletId(publicKey);
    },
    onError: (error) => {
      console.error('Wallet connection failed:', error);
      notify(error.message || 'Failed to connect wallet. Please try again.', 'error');
    },
  });
};
