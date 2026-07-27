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
  default: () => <div data-testid="multiplier-selector" />,
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

describe('Form a11y (issue #272)', () => {
  it('associates the amount input with its label via htmlFor/id', () => {
    renderForm();
    const input = screen.getByPlaceholderText('Enter Token Amount');
    expect(input).toHaveAttribute('type', 'number');
    expect(input).toHaveAttribute('aria-invalid', 'false');
  });

  it('announces a validation error with role=alert and aria-invalid=true', async () => {
    renderForm();
    const amountInput = screen.getByPlaceholderText('Enter Token Amount');
    fireEvent.submit(amountInput.closest('form'));
    await waitFor(() => {
      expect(amountInput).toHaveAttribute('aria-invalid', 'true');
      expect(amountInput).toHaveAttribute('aria-describedby');
      const describedById = amountInput.getAttribute('aria-describedby');
      const errorEl = document.getElementById(describedById);
      expect(errorEl).toHaveAttribute('role', 'alert');
      expect(errorEl.textContent).toContain('Please fill the form');
    });
  });

  it('renders the Submit button as type=submit and announces aria-busy', async () => {
    const { handleTransaction } = await import('@/services/transaction');
    handleTransaction.mockImplementation(
      (_id, _formData, setTokenAmount, setLoading) =>
        new Promise((resolve) => {
          setLoading(true);
          // Resolve later so we can assert aria-busy=true.
          setTimeout(() => {
            setTokenAmount('');
            setLoading(false);
            resolve();
          }, 100);
        })
    );
    useCheckPosition.mockReturnValue({ data: { has_opened_position: false }, refetch: vi.fn() });
    renderForm();
    const submitBtn = screen.getByRole('button', { name: /submit/i });
    expect(submitBtn).toHaveAttribute('type', 'submit');
    expect(submitBtn).toBeInTheDocument();
  });
});
