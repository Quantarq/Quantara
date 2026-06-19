import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import NotFound from './NotFound';

/**
 * Integration test verifying that the catch-all 404 route renders
 * the NotFound page for any undefined path.
 */
describe('App 404 catch-all route', () => {
  it('renders NotFound for an unknown route', () => {
    render(
      <MemoryRouter initialEntries={['/this-path-does-not-exist']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('404')).toBeTruthy();
    expect(
      screen.getByRole('heading', { name: /page not found/i })
    ).toBeTruthy();
  });

  it('does not render NotFound for the home route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Home')).toBeTruthy();
    expect(screen.queryByText('404')).toBeNull();
  });
});