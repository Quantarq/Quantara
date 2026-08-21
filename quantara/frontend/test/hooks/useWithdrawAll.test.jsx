import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import useWithdrawAll from '../../src/hooks/useWithdrawAll';
import { axiosInstance, getAuthHeaders } from '../../src/utils/axios';
import { sendWithdrawAllTransaction } from '../../src/services/transaction';

vi.mock('../../src/utils/axios', () => ({
  axiosInstance: { get: vi.fn(), post: vi.fn() },
  getAuthHeaders: vi.fn(),
}));

vi.mock('../../src/services/transaction', () => ({
  sendWithdrawAllTransaction: vi.fn(),
}));

vi.mock('../../src/components/layout/notifier/Notifier', () => ({
  notify: vi.fn(),
  ToastWithLink: vi.fn(),
}));

const AUTH_HEADERS = {
  'x-wallet-id': 'GABC123',
  'x-nonce': 'nonce',
  'x-signature': 'sig',
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useWithdrawAll', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAuthHeaders.mockResolvedValue(AUTH_HEADERS);
  });

  it('fetches withdraw-all data and closes the position via POST with auth headers', async () => {
    axiosInstance.post.mockResolvedValueOnce({
      data: {
        repay_data: {
          position_id: 'pos-1',
          contract_address: 'C123',
          supply_token: 'S',
          debt_token: 'D',
        },
        tokens: [],
      },
    });
    sendWithdrawAllTransaction.mockResolvedValue({ transaction_hash: 'txhash' });

    const { result } = renderHook(() => useWithdrawAll(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.withdrawAll('GABC123');
    });

    await waitFor(() => expect(sendWithdrawAllTransaction).toHaveBeenCalled());

    expect(getAuthHeaders).toHaveBeenCalledWith('GABC123');
    expect(axiosInstance.post).toHaveBeenCalledWith(
      '/api/get-withdraw-all-data',
      {},
      { headers: AUTH_HEADERS },
    );
    expect(axiosInstance.post).toHaveBeenCalledWith(
      '/api/close-position/pos-1',
      { transaction_hash: 'txhash' },
      { headers: AUTH_HEADERS },
    );
  });
});
