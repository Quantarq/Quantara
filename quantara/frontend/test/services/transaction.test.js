import { getWalletPublicKey } from '../../src/services/wallet';
import { invokeSorobanContract } from '../../src/services/soroban';
import { sendTransaction, closePosition, handleTransaction } from '../../src/services/transaction';
import { axiosInstance } from '../../src/utils/axios';
import { mockBackendUrl } from '../constants';
import { expect, describe, it, beforeEach, vi } from 'vitest';

vi.mock('../../src/services/wallet', () => ({
  getWalletPublicKey: vi.fn(),
  signStellarTransaction: vi.fn(),
  getNetworkPassphrase: vi.fn(),
}));

vi.mock('../../src/services/soroban', () => ({
  invokeSorobanContract: vi.fn(),
}));

vi.mock('../../src/utils/axios', () => ({
  axiosInstance: {
    get: vi.fn(),
    post: vi.fn(),
  },
  getAuthHeaders: vi.fn().mockResolvedValue({ 'x-wallet-id': 'mock', 'x-nonce': 'mock', 'x-signature': 'mock' }),
}));
vi.mock('../../src/services/contract');

describe('Transaction Functions', () => {
  const mockTransactionHash = 'a1b2c3d4e5f6g7h8i9j0';
  const mockContractAddress = 'CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5';
  const mockWalletId = 'GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2';

  beforeEach(() => {
    vi.clearAllMocks();
    getWalletPublicKey.mockResolvedValue(mockWalletId);
    invokeSorobanContract.mockResolvedValue({ transaction_hash: mockTransactionHash });
    process.env.VITE_APP_BACKEND_URL = mockBackendUrl;
  });

  afterEach(() => {
    delete process.env.VITE_APP_BACKEND_URL;
  });

  describe('sendTransaction', () => {
    const validContractCallData = {
      pool_key: 'mock_pool_key',
      deposit_data: {
        token: 'mock_token',
        amount: '1000',
      },
    };

    it('should prepare a Soroban contract transaction', async () => {
      const result = await sendTransaction(validContractCallData, mockContractAddress);

      expect(getWalletPublicKey).toHaveBeenCalled();
      expect(result).toHaveProperty('transaction_hash');
    });

    it('should throw error if wallet is not connected', async () => {
      getWalletPublicKey.mockResolvedValue(null);

      await expect(sendTransaction(validContractCallData, mockContractAddress)).rejects.toThrow(
        'Wallet is not connected'
      );
    });
  });

  describe('closePosition', () => {
    const mockTransactionData = {
      contract_address: mockContractAddress,
      position_id: 1,
    };

    it('should prepare a close position transaction', async () => {
      const result = await closePosition(mockTransactionData);

      expect(getWalletPublicKey).toHaveBeenCalled();
      expect(result).toHaveProperty('transaction_hash');
    });

    it('should throw error if wallet is not connected', async () => {
      getWalletPublicKey.mockResolvedValue(null);

      await expect(closePosition(mockTransactionData)).rejects.toThrow(
        'Wallet is not connected'
      );
    });
  });

  describe('handleTransaction', () => {
    const mockSetTokenAmount = vi.fn();
    const mockSetLoading = vi.fn();
    const mockFormData = { position_id: 1 };

    beforeEach(() => {
      mockSetTokenAmount.mockClear();
      mockSetLoading.mockClear();
      axiosInstance.post.mockResolvedValue({
        data: {
          position_id: 1,
          contract_address: mockContractAddress,
          pool_key: { token1: 'mock_debt_token' },
          deposit_data: { token: 'mock_deposit_token', amount: '1000', multiplier: 3 },
        },
      });
    });

    it('should handle successful transaction flow', async () => {
      axiosInstance.get.mockResolvedValueOnce({
        data: { status: 'open' },
      });

      await handleTransaction(mockWalletId, mockFormData, mockSetTokenAmount, mockSetLoading);

      expect(mockSetLoading).toHaveBeenCalledWith(true);
      expect(getWalletPublicKey).toHaveBeenCalled();
      expect(axiosInstance.post).toHaveBeenCalledWith('/api/create-position', mockFormData, { headers: { 'x-wallet-id': 'mock', 'x-nonce': 'mock', 'x-signature': 'mock' } });
      expect(invokeSorobanContract).toHaveBeenCalled();
      expect(axiosInstance.get).toHaveBeenCalledWith('/api/open-position', {
        params: { position_id: 1, transaction_hash: mockTransactionHash },
      });
      expect(mockSetTokenAmount).toHaveBeenCalledWith('');
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });

    it('should handle missing wallet connection', async () => {
      getWalletPublicKey.mockResolvedValue(null);

      await handleTransaction(mockWalletId, mockFormData, mockSetTokenAmount, mockSetLoading);

      expect(mockSetLoading).toHaveBeenCalledWith(true);
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });

    it('should handle create position error', async () => {
      const mockError = new Error('Create position failed');
      axiosInstance.post.mockRejectedValue(mockError);

      console.error = vi.fn();

      await handleTransaction(mockWalletId, mockFormData, mockSetTokenAmount, mockSetLoading);

      expect(console.error).toHaveBeenCalledWith('Failed to create position:', mockError);
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });
});
