import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DashboardPage from '@/pages/dashboard/Dashboard';

vi.mock('@/hooks/useDashboardData', () => ({ default: vi.fn() }));
vi.mock('@/hooks/useClosePosition', () => ({
  useClosePosition: vi.fn(),
  useCheckPosition: vi.fn(),
}));
vi.mock('@/stores/useWalletStore', () => ({ useWalletStore: vi.fn() }));
vi.mock('@/components/layout/sidebar/Sidebar', () => ({ default: () => <div /> }));
vi.mock('@/hooks/useCheckMobile', () => ({ useCheckMobile: vi.fn(() => false) }));
vi.mock('@/components/ui/telegram-notification/TelegramNotification', () => ({
  TelegramNotification: () => <div data-testid="telegram-notification" />,
}));
vi.mock('@/components/dashboard/dashboardCard/DashboardInfoCard', () => ({
  default: () => <div data-testid="dashboard-info-card" />,
}));

import useDashboardData from '@/hooks/useDashboardData';
import { useClosePosition, useCheckPosition } from '@/hooks/useClosePosition';
import { useWalletStore } from '@/stores/useWalletStore';

const createClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderDashboard = () =>
  render(
    <QueryClientProvider client={createClient()}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>
  );

beforeEach(() => {
  useWalletStore.mockReturnValue({ walletId: 'wallet-1' });
  useClosePosition.mockReturnValue({ mutate: vi.fn(), isLoading: false });
  useCheckPosition.mockReturnValue({ data: { has_opened_position: true } });
});

describe('DashboardPage', () => {
  it('renders loading spinner when data is loading', () => {
    useDashboardData.mockReturnValue({
      cardData: undefined, healthFactor: null, startSum: null,
      currentSum: null, depositedData: null, isLoading: true,
    });
    renderDashboard();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders Health Factor and Borrow Balance cards', () => {
    useDashboardData.mockReturnValue({
      cardData: { borrowed: '1.5' }, healthFactor: '1.85',
      startSum: '100', currentSum: '150', depositedData: {}, isLoading: false,
    });
    renderDashboard();
    expect(screen.getByText('Health Factor')).toBeInTheDocument();
    expect(screen.getByText('Borrow Balance')).toBeInTheDocument();
  });

  it('renders Redeem button enabled when position is open', () => {
    useDashboardData.mockReturnValue({
      cardData: { borrowed: '1.5' }, healthFactor: '2.0',
      startSum: '100', currentSum: '120', depositedData: {}, isLoading: false,
    });
    renderDashboard();
    expect(screen.getByRole('button', { name: /redeem/i })).toBeEnabled();
  });

  it('renders Redeem button disabled when no opened position', () => {
    useCheckPosition.mockReturnValue({ data: { has_opened_position: false } });
    useDashboardData.mockReturnValue({
      cardData: { borrowed: '1.5' }, healthFactor: '2.0',
      startSum: '100', currentSum: '120', depositedData: {}, isLoading: false,
    });
    renderDashboard();
    expect(screen.getByRole('button', { name: /redeem/i })).toBeDisabled();
  });

  it('shows Closing... text when close position is in progress', () => {
    useClosePosition.mockReturnValue({ mutate: vi.fn(), isLoading: true });
    useDashboardData.mockReturnValue({
      cardData: { borrowed: '1.5' }, healthFactor: '2.0',
      startSum: '100', currentSum: '120', depositedData: {}, isLoading: false,
    });
    renderDashboard();
    expect(screen.getByRole('button', { name: /closing/i })).toBeInTheDocument();
  });
});
