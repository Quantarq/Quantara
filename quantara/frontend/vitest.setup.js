import { TextEncoder, TextDecoder } from 'util';
import '@testing-library/jest-dom';

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// ---- Telemetry mocks (Issue #277) -----------------------------------------
// Sentry and web-vitals are mocked globally so tests don't open any
// network connections and don't pollute the test output with breadcrumb
// logs. Tests that need to assert telemetry side effects import the
// mocked module explicitly via vi.mock('@sentry/react', …).
vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  startTransaction: vi.fn(() => ({
    setStatus: vi.fn(),
    setMeasurement: vi.fn(),
    finish: vi.fn(),
  })),
  addBreadcrumb: vi.fn(),
  captureException: vi.fn(),
  browserTracingIntegration: vi.fn(() => ({ name: 'BrowserTracing' })),
  getCurrentHub: () => ({ getScope: () => ({ getTransaction: () => null }) }),
}));

vi.mock('web-vitals', () => ({
  onLCP: vi.fn(),
  onCLS: vi.fn(),
  onINP: vi.fn(),
  onFCP: vi.fn(),
  onTTFB: vi.fn(),
}));

// ---- qrcode mock -----------------------------------------------------------
// The `qrcode` package uses canvas APIs that aren't available in jsdom;
// mock it to return a deterministic stub.
vi.mock('qrcode', () => ({
  toCanvas: vi.fn((el) => {
    if (el) el.dataset.qrStub = '1';
    return Promise.resolve();
  }),
}));
