const mockStarknet = {
    isConnected: true,
    account: {
      deployContract: jest.fn().mockResolvedValue({
        transaction_hash: '0xabc...',
        contract_address: '0xdef...'
      }),
      waitForTransaction: jest.fn().mockResolvedValue(true),
    },
  };
  
  export const connect = jest.fn().mockResolvedValue(mockStarknet);
  