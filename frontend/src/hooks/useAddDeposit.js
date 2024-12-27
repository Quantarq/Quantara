import { useMutation } from '@tanstack/react-query';
import { axiosInstance } from 'utils/axios';
import { notify } from 'components/layout/notifier/Notifier';
import useDashboardData from './useDashboardData';

export const useAddDeposit = () => {
  const { data: dashboardData } = useDashboardData();
  const mutation = useMutation({
    mutationFn: async ({ positionId, amount, tokenSymbol }) => {
      if (!dashboardData?.position_id) {
        return notify('No position found', 'error');
      }

      const { data } = await axiosInstance.post(`/api/add-extra-deposit/${positionId}`, {
        position_id: dashboardData.position_id,
        amount: parseFloat(amount),
        token_symbol: tokenSymbol,
      });
      return data;
    },
    onSuccess: () => {
      notify('Successfully deposited!', 'success');
    },
    onError: (error) => {
      notify(error.response?.data?.message || 'Failed to process deposit', 'error');
    },
  });

  return mutation;
};
