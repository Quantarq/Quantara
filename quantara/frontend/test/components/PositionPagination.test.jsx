import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PositionPagination from '@/pages/position-history/PositionPagination';

const defaultProps = {
  currentPage: 1,
  setCurrentPage: vi.fn(),
  isPending: false,
  tableData: { total_count: 30 },
  positionsOnPage: 10,
};

const renderPagination = (props = {}) =>
  render(<PositionPagination {...defaultProps} {...props} />);

describe('PositionPagination', () => {
  it('renders correct number of page buttons', () => {
    renderPagination();
    // 30 items / 10 per page = 3 pages
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('calls setCurrentPage when a page button is clicked', () => {
    const setCurrentPage = vi.fn();
    renderPagination({ setCurrentPage });
    fireEvent.click(screen.getByText('2'));
    expect(setCurrentPage).toHaveBeenCalledWith(2);
  });

  it('disables prev button on first page', () => {
    renderPagination({ currentPage: 1 });
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toBeDisabled();
  });

  it('disables next button on last page', () => {
    renderPagination({ currentPage: 3 });
    const buttons = screen.getAllByRole('button');
    expect(buttons[buttons.length - 1]).toBeDisabled();
  });

  it('calls setCurrentPage with next page on next button click', () => {
    const setCurrentPage = vi.fn();
    renderPagination({ currentPage: 1, setCurrentPage });
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[buttons.length - 1]);
    expect(setCurrentPage).toHaveBeenCalledWith(2);
  });

  it('does not change page when isPending is true', () => {
    const setCurrentPage = vi.fn();
    renderPagination({ isPending: true, setCurrentPage });
    fireEvent.click(screen.getByText('2'));
    expect(setCurrentPage).not.toHaveBeenCalled();
  });
});
