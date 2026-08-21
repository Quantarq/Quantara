import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { useClosePosition } from '../../src/hooks/useClosePosition';
import { useWalletStore } from '../../src/stores/useWalletStore';
import { axiosInstance, getAuthHeaders } from '../../src/utils/axios';
import { closePosition } from '../../src/services/transaction';

vi.mock('../../src/utils/axios', () => ({
  axiosInstance: { get: vi.fn(), post: vi.fn() },
  getAuthHeaders: vi.fn(),
}));

vi.mock('../../src/services/transaction', () => ({
  closePosition: vi.fn(),
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

describe('useClosePosition', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWalletStore.setState({ walletId: 'GABC123' });
    getAuthHeaders.mockResolvedValue(AUTH_HEADERS);
  });

  afterEach(() => {
    useWalletStore.setState({ walletId: null });
  });

  it('fetches repay data and closes the position via POST with auth headers', async () => {
    axiosInstance.post.mockResolvedValueOnce({
      data: {
        position_id: 'pos-1',
        contract_address: 'C123',
        supply_token: 'S',
        debt_token: 'D',
      },
    });
    closePosition.mockResolvedValue({ transaction_hash: 'txhash' });

    const { result } = renderHook(() => useClosePosition(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(closePosition).toHaveBeenCalled());

    expect(getAuthHeaders).toHaveBeenCalledWith('GABC123');
    expect(axiosInstance.post).toHaveBeenCalledWith(
      '/api/get-repay-data',
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
