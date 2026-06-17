import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PositionHistory from '@/pages/position-history/PositionHistory';

vi.mock('@/hooks/usePositionHistory', () => ({ usePositionHistoryTable: vi.fn() }));
vi.mock('@/hooks/useDashboardData', () => ({ default: vi.fn() }));
vi.mock('@/components/layout/sidebar/Sidebar', () => ({ default: () => <div /> }));
vi.mock('@/hooks/useCheckMobile', () => ({ useCheckMobile: vi.fn(() => false) }));

import { usePositionHistoryTable } from '@/hooks/usePositionHistory';
import useDashboardData from '@/hooks/useDashboardData';

const createClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderHistory = () =>
  render(
    <QueryClientProvider client={createClient()}>
      <MemoryRouter>
        <PositionHistory />
      </MemoryRouter>
    </QueryClientProvider>
  );

beforeEach(() => {
  useDashboardData.mockReturnValue({ data: { health_ratio: '1.5', borrowed: '2.0' }, isLoading: false });
});

describe('PositionHistory', () => {
  it('shows loading spinner when data is pending', () => {
    usePositionHistoryTable.mockReturnValue({ data: null, isPending: true });
    renderHistory();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders empty state message when no positions', () => {
    usePositionHistoryTable.mockReturnValue({ data: { positions: [], total_count: 0 }, isPending: false });
    renderHistory();
    expect(screen.getByText('No opened positions')).toBeInTheDocument();
  });

  it('renders position rows when positions exist', () => {
    usePositionHistoryTable.mockReturnValue({
      data: {
        positions: [{
          id: '1', token_symbol: 'ETH', amount: '1.5', created_at: '2024-01-01',
          status: 'opened', start_price: '3000', multiplier: '2',
          is_liquidated: false, closed_at: null,
        }],
        total_count: 1,
      },
      isPending: false,
    });
    renderHistory();
    expect(screen.getByText('ETH')).toBeInTheDocument();
    expect(screen.getAllByText('1.5').length).toBeGreaterThan(0);
    expect(screen.getByText('opened')).toBeInTheDocument();
  });

  it('renders table column headers', () => {
    usePositionHistoryTable.mockReturnValue({ data: { positions: [], total_count: 0 }, isPending: false });
    renderHistory();
    expect(screen.getByText('Token')).toBeInTheDocument();
    expect(screen.getByText('Amount')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('renders pagination controls when positions exist', () => {
    usePositionHistoryTable.mockReturnValue({
      data: {
        positions: [{
          id: '1', token_symbol: 'USDC', amount: '100', created_at: '2024-01-01',
          status: 'closed', start_price: '1', multiplier: '3',
          is_liquidated: false, closed_at: '2024-01-10',
        }],
        total_count: 1,
      },
      isPending: false,
    });
    renderHistory();
    // pagination renders prev/next buttons
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(3); // prev + page + next
  });
});
