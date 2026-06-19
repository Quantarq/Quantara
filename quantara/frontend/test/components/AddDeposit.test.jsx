import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AddDeposit } from '@/pages/add-deposit/AddDeposit';

vi.mock('@/hooks/useDashboardData', () => ({ default: vi.fn() }));
vi.mock('@/hooks/useAddDeposit', () => ({ useAddDeposit: vi.fn() }));
vi.mock('@/components/layout/sidebar/Sidebar', () => ({ default: () => <div /> }));
vi.mock('@/hooks/useCheckMobile', () => ({ useCheckMobile: vi.fn(() => false) }));

import useDashboardData from '@/hooks/useDashboardData';
import { useAddDeposit } from '@/hooks/useAddDeposit';

const createClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderAddDeposit = () =>
  render(
    <QueryClientProvider client={createClient()}>
      <MemoryRouter>
        <AddDeposit />
      </MemoryRouter>
    </QueryClientProvider>
  );

beforeEach(() => {
  useAddDeposit.mockReturnValue({ mutate: vi.fn(), isLoading: false });
  useDashboardData.mockReturnValue({
    data: { health_ratio: '1.8', borrowed: '500', position_id: 'pos-1' },
    isLoading: false,
  });
});

describe('AddDeposit', () => {
  it('renders the deposit prompt heading', () => {
    renderAddDeposit();
    expect(screen.getByText('Please make a deposit')).toBeInTheDocument();
  });

  it('renders the amount input with default value 0', () => {
    renderAddDeposit();
    expect(screen.getByPlaceholderText('0.00')).toBeInTheDocument();
  });

  it('renders the Deposit button disabled when amount is 0', () => {
    renderAddDeposit();
    expect(screen.getByRole('button', { name: /deposit/i })).toBeDisabled();
  });

  it('enables Deposit button when amount is entered', () => {
    renderAddDeposit();
    fireEvent.change(screen.getByPlaceholderText('0.00'), { target: { value: '5' } });
    expect(screen.getByRole('button', { name: /deposit/i })).toBeEnabled();
  });

  it('shows Processing... when deposit is in progress', () => {
    useAddDeposit.mockReturnValue({ mutate: vi.fn(), isLoading: true });
    renderAddDeposit();
    expect(screen.getByRole('button', { name: /processing/i })).toBeInTheDocument();
  });

  it('renders Health Factor and Borrow Balance cards', () => {
    renderAddDeposit();
    expect(screen.getByText('Health Factor')).toBeInTheDocument();
    expect(screen.getByText('Borrow Balance')).toBeInTheDocument();
  });
});
