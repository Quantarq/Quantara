import { useMutation } from '@tanstack/react-query';
import { axiosInstance, getAuthHeaders } from '../utils/axios';
import { notify } from '../components/layout/notifier/Notifier';
import { sendWithdrawAllTransaction } from '../services/transaction';

/**
 * Hook for the Withdraw All operation: closes the position and withdraws
 * all remaining collateral from the Soroban contract.
 *
 * @returns {{ withdrawAll: Function, isLoading: boolean }}
 */
const useWithdrawAll = () => {
  const mutation = useMutation({
    mutationFn: async (walletId) => {
      if (!walletId) throw new Error('Wallet ID is required.');

      const authHeaders = await getAuthHeaders(walletId);

      const { data: withdraw_data } = await axiosInstance.post(
        '/api/get-withdraw-all-data',
        {},
        { headers: authHeaders },
      );

      const { transaction_hash } = await sendWithdrawAllTransaction(
        withdraw_data,
        withdraw_data.repay_data.contract_address
      );

      await axiosInstance.post(
        `/api/close-position/${withdraw_data.repay_data.position_id}`,
        { transaction_hash },
        { headers: authHeaders },
      );
    },
    onSuccess: () => {
      notify('Withdraw All operation completed successfully!', 'success');
    },
    onError: (error) => {
      notify(error?.message || 'Failed to complete the Withdraw All operation.', 'error');
    },
  });

  return {
    withdrawAll: mutation.mutate,
    isLoading: mutation.isPending,
  };
};

export default useWithdrawAll;
