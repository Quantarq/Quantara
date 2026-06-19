import { useWalletStore } from './useWalletStore';
import axios from 'axios';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Use Vitest's structural mocking utility
vi.mock('axios');

describe('useWalletStore - Cookie Session Migration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the Zustand store state before each test run
    useWalletStore.setState({ walletId: null, isInitializing: true });
  });

  it('should successfully resolve walletId when a secure httpOnly session cookie exists', async () => {
    const mockWalletId = 'G...STARK';
    vi.mocked(axios.get).mockResolvedValueOnce({ data: { walletId: mockWalletId } });

    await useWalletStore.getState().initializeSession();

    expect(useWalletStore.getState().walletId).toBe(mockWalletId);
    expect(useWalletStore.getState().isInitializing).toBe(false);
    expect(axios.get).toHaveBeenCalledWith('/api/auth/session');
  });

  it('should set walletId to null if the session check returns a 401 unauthorized or fails', async () => {
    vi.mocked(axios.get).mockRejectedValueOnce(new Error('Unauthorized'));

    await useWalletStore.getState().initializeSession();

    expect(useWalletStore.getState().walletId).toBe(null);
    expect(useWalletStore.getState().isInitializing).toBe(false);
  });

  it('should cleanly flush state components out of memory on logout execution patterns', () => {
    useWalletStore.setState({ walletId: 'G...STARK' });
    
    useWalletStore.getState().clearWallet();

    expect(useWalletStore.getState().walletId).toBe(null);
  });
});