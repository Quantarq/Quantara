/**
 * Quantara entry point.
 *
 * Telemetry initialization (Issue #277) MUST run *before* React mounts so
 * that Sentry's page-load transaction can capture the React render
 * itself. The `initTelemetry()` call is a no-op when `VITE_SENTRY_DSN` is
 * unset, so local development and CI tests are unaffected.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router } from 'react-router-dom';
import './i18n';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { initTelemetry } from './services/telemetry';
import App from './App';

// Initialize telemetry as early as possible so Sentry can capture the
// React mount transaction. Idempotent — App.jsx's mount call is a no-op
// in this case (see Issue #277 acceptance criterion).
initTelemetry();

const queryClient = new QueryClient();

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <QueryClientProvider client={queryClient}>
    <Router>
      <App />
    </Router>
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
);
