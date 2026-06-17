import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Form from '@/pages/form/Form';

vi.mock('@/stores/useWalletStore', () => ({ useWalletStore: vi.fn() }));
vi.mock('@/hooks/useConnectWallet', () => ({ useConnectWallet: vi.fn() }));
vi.mock('@/hooks/useClosePosition', () => ({ useCheckPosition: vi.fn() }));
vi.mock('@/hooks/useHealthRatio', () => ({ useHealthFactor: vi.fn() }));
vi.mock('@/services/transaction', () => ({ handleTransaction: vi.fn() }));
vi.mock('@/components/layout/notifier/Notifier', () => ({ notify: vi.fn() }));
vi.mock('@/components/ui/balance-cards/BalanceCards', () => ({
  default: () => <div data-testid="balance-cards" />,
}));
vi.mock('@/components/ui/multiplier-selector/MultiplierSelector', () => ({
  default: ({ setSelectedMultiplier }) => (
    <div data-testid="multiplier-selector">
      <button onClick={() => setSelectedMultiplier('2')}>Select 2x</button>
    </div>
  ),
}));

import { useWalletStore } from '@/stores/useWalletStore';
import { useConnectWallet } from '@/hooks/useConnectWallet';
import { useCheckPosition } from '@/hooks/useClosePosition';
import { useHealthFactor } from '@/hooks/useHealthRatio';

const createClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderForm = () =>
  render(
    <QueryClientProvider client={createClient()}>
      <MemoryRouter>
        <Form />
      </MemoryRouter>
    </QueryClientProvider>
  );

beforeEach(() => {
  useWalletStore.mockReturnValue({ walletId: 'wallet-1', setWalletId: vi.fn() });
  useConnectWallet.mockReturnValue({ mutate: vi.fn() });
  useCheckPosition.mockReturnValue({ data: { has_opened_position: false }, refetch: vi.fn() });
  useHealthFactor.mockReturnValue({ healthFactor: '1.75', isLoading: false });
});

describe('Form', () => {
  it('renders the form heading', () => {
    renderForm();
    expect(screen.getByText('Please submit your leverage details')).toBeInTheDocument();
  });

  it('renders the token amount input', () => {
    renderForm();
    expect(screen.getByPlaceholderText('Enter Token Amount')).toBeInTheDocument();
  });

  it('renders the Submit button', () => {
    renderForm();
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
  });

  it('renders estimated health factor value', () => {
    renderForm();
    expect(screen.getByText('Estimated Health Factor Level:')).toBeInTheDocument();
    expect(screen.getByText('1.75')).toBeInTheDocument();
  });

  it('shows Loading... for health factor when loading', () => {
    useHealthFactor.mockReturnValue({ healthFactor: null, isLoading: true });
    renderForm();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows validation error when submitting with empty fields', async () => {
    const { notify } = await import('@/components/layout/notifier/Notifier');
    renderForm();
    fireEvent.submit(screen.getByRole('button', { name: /submit/i }).closest('form'));
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith('Please fill the form', 'error');
    });
  });

  it('renders the Select Multiplier label', () => {
    renderForm();
    expect(screen.getByText('Select Multiplier')).toBeInTheDocument();
  });
});
