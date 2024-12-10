import { useQuery } from '@tanstack/react-query';
import { ONE_HOUR_IN_MILLISECONDS } from '../utils/constants';
import { axiosInstance } from 'utils/axios';

export const useMaxMultiplier = () => {
  const { data, isPending, error } = useQuery({
    queryKey: ['max-multiplier'],
    queryFn: async () => {
      const response = await axiosInstance.get(`/api/get-multipliers`);
      return response.data.multipliers;
    },
    staleTime: ONE_HOUR_IN_MILLISECONDS,
    refetchInterval: ONE_HOUR_IN_MILLISECONDS,
  });

  return { data, isLoading: isPending, error };
};
