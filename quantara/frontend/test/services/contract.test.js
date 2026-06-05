import { getWalletPublicKey, signStellarTransaction, getNetworkPassphrase } from '../../src/services/wallet';
import { axiosInstance } from '../../src/utils/axios';
import { deployContract, checkAndDeployContract } from '../../src/services/contract';
import { getSorobanServer, pollForTransaction } from '../../src/services/soroban';
import { SorobanRpc, Operation, TransactionBuilder, Address, scValToNative } from '@stellar/stellar-sdk';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock dependencies
vi.mock('../../src/services/wallet', () => ({
  getWalletPublicKey: vi.fn(),
  signStellarTransaction: vi.fn(),
  getNetworkPassphrase: vi.fn(() => 'Test SDF Network ; September 2015'),
}));

vi.mock('../../src/utils/axios');
vi.mock('../../src/utils/constants', () => ({
  SOROBAN_WASM_HASH: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
}));

vi.mock('../../src/services/soroban', () => ({
  getSorobanServer: vi.fn(),
  pollForTransaction: vi.fn(),
}));

vi.mock('../../src/components/layout/notifier/Notifier', () => ({
  notify: vi.fn(),
  ToastWithLink: vi.fn(() => 'mock-toast-element'),
}));

// Mock @stellar/stellar-sdk - TransactionBuilder must be a constructor
vi.mock('@stellar/stellar-sdk', () => {
  const mockSorobanRpc = {
    Server: vi.fn(),
    isSimulationSuccess: vi.fn(),
  };

  // TransactionBuilder needs to be usable with `new` and have static fromXDR
  const mockTxBuilder = vi.fn(() => ({
    addOperation: vi.fn().mockReturnThis(),
    setTimeout: vi.fn().mockReturnThis(),
    build: vi.fn(),
  }));
  mockTxBuilder.fromXDR = vi.fn(() => 'mock-signed-tx');

  const mockOperation = {
    createCustomContract: vi.fn(() => 'mock-create-custom-contract-op'),
  };
  const mockAddress = {
    fromString: vi.fn(() => 'mock-address-object'),
  };
  const mockScValToNative = vi.fn();

  return {
    SorobanRpc: mockSorobanRpc,
    Operation: mockOperation,
    TransactionBuilder: mockTxBuilder,
    Address: mockAddress,
    scValToNative: mockScValToNative,
  };
});

describe('Contract Deployment Tests', () => {
  const mockWalletId = 'GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2';
  const mockContractId = 'CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5';
  const mockTxHash = 'abc123def456';

  // Soroban mock objects
  let mockServer;
  let mockAccount;
  let mockSimulation;
  let mockAssembledTx;
  let mockSendResponse;
  let mockPollResult;

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup Soroban RPC server mock
    mockAccount = { id: mockWalletId, sequenceNumber: '12345' };
    mockAssembledTx = {
      toXDR: vi.fn(() => 'mock-assembled-xdr'),
    };
    mockSendResponse = {
      status: 'PENDING',
      hash: mockTxHash,
    };
    mockPollResult = {
      status: 'SUCCESS',
      returnValue: 'mock-sc-val',
    };

    mockServer = {
      getAccount: vi.fn().mockResolvedValue(mockAccount),
      simulateTransaction: vi.fn(),
      sendTransaction: vi.fn(),
      getTransaction: vi.fn(),
    };

    mockSimulation = {
      transaction: mockAssembledTx,
      error: null,
    };

    mockServer.simulateTransaction.mockResolvedValue(mockSimulation);
    mockServer.sendTransaction.mockResolvedValue(mockSendResponse);

    getSorobanServer.mockReturnValue(mockServer);
    SorobanRpc.isSimulationSuccess.mockReturnValue(true);
    scValToNative.mockReturnValue(mockContractId);

    vi.mocked(axiosInstance.get).mockReset();
  });

  describe('deployContract', () => {
    it('should successfully deploy a Soroban contract', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      signStellarTransaction.mockResolvedValue('signed-xdr');
      pollForTransaction.mockResolvedValue(mockPollResult);

      const result = await deployContract(mockWalletId);

      // Verify wallet check
      expect(getWalletPublicKey).toHaveBeenCalled();

      // Verify WASM hash was used
      expect(Operation.createCustomContract).toHaveBeenCalledWith(
        expect.objectContaining({
          wasmHash: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
          address: 'mock-address-object',
        })
      );
      expect(Operation.createCustomContract).toHaveBeenCalledWith(
        expect.objectContaining({
          salt: expect.any(Uint8Array),
        })
      );

      // Verify transaction flow
      expect(mockServer.getAccount).toHaveBeenCalledWith(mockWalletId);
      expect(mockServer.simulateTransaction).toHaveBeenCalled();
      expect(SorobanRpc.isSimulationSuccess).toHaveBeenCalledWith(mockSimulation);
      expect(signStellarTransaction).toHaveBeenCalledWith('mock-assembled-xdr', {
        network: 'TESTNET',
      });
      expect(mockServer.sendTransaction).toHaveBeenCalled();
      expect(pollForTransaction).toHaveBeenCalledWith(mockServer, mockTxHash);

      // Verify result
      expect(result).toEqual({
        transactionHash: mockTxHash,
        contractAddress: mockContractId,
      });
    });

    it('should handle missing wallet connection', async () => {
      getWalletPublicKey.mockResolvedValue(null);

      await expect(deployContract(mockWalletId)).rejects.toThrow(
        'Please connect your Freighter wallet first'
      );

      expect(mockServer.getAccount).not.toHaveBeenCalled();
    });

    it('should handle wallet errors', async () => {
      getWalletPublicKey.mockRejectedValue(new Error('Wallet error'));
      await expect(deployContract(mockWalletId)).rejects.toThrow('Wallet error');
    });

    it('should handle simulation failure', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      SorobanRpc.isSimulationSuccess.mockReturnValue(false);
      mockSimulation.error = 'Insufficient budget';

      await expect(deployContract(mockWalletId)).rejects.toThrow(
        'Contract deployment simulation failed: Insufficient budget'
      );
    });

    it('should handle submission error', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      signStellarTransaction.mockResolvedValue('signed-xdr');
      mockServer.sendTransaction.mockResolvedValue({
        status: 'ERROR',
        errorResult: { error: 'Insufficient fee' },
      });

      await expect(deployContract(mockWalletId)).rejects.toThrow(
        'Soroban deployment submission error: Insufficient fee'
      );
    });

    it('should handle missing contract address in result', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      signStellarTransaction.mockResolvedValue('signed-xdr');
      pollForTransaction.mockResolvedValue({
        status: 'SUCCESS',
        returnValue: null,
      });

      await expect(deployContract(mockWalletId)).rejects.toThrow(
        'Deployment succeeded but no contract address was returned.'
      );
    });

    it('should handle invalid contract address format', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      signStellarTransaction.mockResolvedValue('signed-xdr');
      scValToNative.mockReturnValue(12345); // Not a string
      pollForTransaction.mockResolvedValue(mockPollResult);

      await expect(deployContract(mockWalletId)).rejects.toThrow(/Invalid contract address/);
    });
  });

  describe('checkAndDeployContract', () => {
    it('should deploy contract if not already deployed', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      signStellarTransaction.mockResolvedValue('signed-xdr');
      pollForTransaction.mockResolvedValue(mockPollResult);

      vi.mocked(axiosInstance.get).mockResolvedValue({
        data: { is_contract_deployed: false },
      });
      vi.mocked(axiosInstance.post).mockResolvedValue({ data: 'success' });

      await checkAndDeployContract(mockWalletId);

      expect(axiosInstance.get).toHaveBeenCalledWith(`/api/check-user?wallet_id=${mockWalletId}`);
      expect(getWalletPublicKey).toHaveBeenCalled();
      expect(axiosInstance.post).toHaveBeenCalledWith('/api/update-user-contract', {
        wallet_id: mockWalletId,
        contract_address: mockContractId,
      });
    });

    it('should skip deployment if contract already exists', async () => {
      vi.mocked(axiosInstance.get).mockResolvedValue({
        data: { is_contract_deployed: true },
      });
      await checkAndDeployContract(mockWalletId);
      expect(axiosInstance.get).toHaveBeenCalledWith(`/api/check-user?wallet_id=${mockWalletId}`);
      expect(getWalletPublicKey).not.toHaveBeenCalled();
      expect(axiosInstance.post).not.toHaveBeenCalled();
    });

    it('should re-throw backend errors', async () => {
      const mockError = new Error('Backend error');
      vi.mocked(axiosInstance.get).mockRejectedValue(mockError);

      await expect(checkAndDeployContract(mockWalletId)).rejects.toThrow('Backend error');
    });

    it('should re-throw deployment errors', async () => {
      getWalletPublicKey.mockResolvedValue(mockWalletId);
      SorobanRpc.isSimulationSuccess.mockReturnValue(false);
      mockSimulation.error = 'Deployment failed';

      vi.mocked(axiosInstance.get).mockResolvedValue({
        data: { is_contract_deployed: false },
      });

      await expect(checkAndDeployContract(mockWalletId)).rejects.toThrow(
        'Contract deployment simulation failed: Deployment failed'
      );
    });
  });
});
