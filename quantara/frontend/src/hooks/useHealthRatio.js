import { useQuery } from '@tanstack/react-query';
import { axiosInstance } from '../utils/axios';
import { logger } from '@/utils/logger';

/** Token configuration for health factor calculation */
const TOKEN_CONFIG = {
  XLM: {
    id: 'stellar',
    collateralFactor: 0.8,
    borrowFactor: 0.9,
    decimals: 7,
  },
  USDC: {
    id: 'usd-coin',
    collateralFactor: 0.85,
    borrowFactor: 0.9,
    decimals: 7,
  },
  ETH: {
    id: 'ethereum',
    collateralFactor: 0.8,
    borrowFactor: 0.9,
    decimals: 7,
  },
};

const fetchTokenPrice = async (tokenId) => {
  const { data } = await axiosInstance.get(
    `https://api.coingecko.com/api/v3/simple/price?ids=${tokenId}&vs_currencies=usd`
  );
  return data[tokenId].usd;
};


/**
 * Calculate the health factor for a proposed position based on token amounts,
 * leverage multiplier, and real-time token prices from CoinGecko.
 *
 * @param {string} selectedToken - The token symbol (XLM, USDC, or ETH)
 * @param {string} tokenAmount - The amount of tokens being deposited
 * @param {string} selectedMultiplier - The leverage multiplier
 * @returns {{ healthFactor: number, tokenPrice: number, isLoading: boolean, isError: boolean }}
 */
export const useHealthFactor = (selectedToken, tokenAmount, selectedMultiplier) => {
  const tokenId = selectedToken ? TOKEN_CONFIG[selectedToken]?.id : null;

  const { data: tokenPrice = 0, error } = useQuery({
    queryKey: ['tokenPrice', tokenId],
    queryFn: () => fetchTokenPrice(tokenId),
    enabled: !!tokenId,
    staleTime: 30000,
    gcTime: 60000,
  });

  const calculateHealthFactor = () => {
    if (!tokenAmount || !selectedMultiplier || !tokenPrice) {
      return 0;
    }

    try {
      const amount = parseFloat(tokenAmount);
      const multiplier = parseFloat(selectedMultiplier);
      const tokenConfig = TOKEN_CONFIG[selectedToken];

      const collateralValue = amount * tokenPrice * tokenConfig.collateralFactor;
      const borrowedAmount = amount * tokenPrice * (multiplier - 1);
      const adjustedDebtValue = borrowedAmount / tokenConfig.borrowFactor;
      const healthFactorValue = collateralValue / adjustedDebtValue;

      return Number(healthFactorValue.toFixed(6));
    } catch (error) {
      logger.error('Error calculating health factor:', error);
      return 0;
    }
  };

  return {
    healthFactor: calculateHealthFactor(),
    tokenPrice,
    isLoading: !error && !tokenPrice,
    isError: !!error,
  };
};
