import { useMutation, useQuery } from '@tanstack/react-query';
import { axiosInstance, getAuthHeaders } from '../utils/axios';
import { closePosition } from '../services/transaction';
import { useWalletStore } from '../stores/useWalletStore';
import { notify } from '../components/layout/notifier/Notifier';

/**
 * Hook for closing a user's leveraged position.
 *
 * Fetches repay data from the backend, invokes the Soroban close_position
 * contract, and notifies the backend of the closure.
 *
 * @returns {useMutation} React Query mutation for position closure
 */
export const useClosePosition = () => {
  const { walletId } = useWalletStore();

  return useMutation({
    mutationFn: async () => {
      if (!walletId) {
        console.error('closePositionEvent: walletId is undefined');
        return;
      }
      const authHeaders = await getAuthHeaders(walletId);
      const response = await axiosInstance.post(
        '/api/get-repay-data',
        {},
        { headers: authHeaders },
      );
      const transactionResult = await closePosition(response.data);
      console.log('TransactionResult', transactionResult);
      await axiosInstance.post(
        `/api/close-position/${response.data.position_id}`,
        { transaction_hash: transactionResult.transaction_hash },
        { headers: authHeaders },
      );
    },
    onError: (error) => {
      console.error('Error during closePositionEvent', error);
      notify(`Error during closePositionEvent: ${error.message}`, 'error');
    },
  });
};


/**
 * Hook for checking whether a user has an open position.
 *
 * @returns {useQuery} React Query result with has_opened_position flag
 */
export const useCheckPosition = () => {
  const { walletId } = useWalletStore();

  return useQuery({
    queryKey: ['hasOpenPosition', walletId],
    queryFn: async () => {
      if (!walletId) return { has_opened_position: false };

      const { data } = await axiosInstance.get('/api/has-user-opened-position', {
        params: { wallet_id: walletId },
      });
      return data;
    },
    enabled: !!walletId,
  });
};
