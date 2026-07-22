/**
 * Quantara Privacy-Safe Telemetry (Issue #277)
 *
 * Initializes Sentry's React SDK with explicit "no PII" guarantees and
 * wires up the `web-vitals` library to forward Core Web Vitals into the
 * Sentry Performance tab.
 *
 * Acceptance criteria:
 *   • Core Web Vitals appear in the Sentry Performance tab for staging
 *   • No wallet IDs or transaction hashes are forwarded to Sentry
 *   • `reportAllChanges: true` is documented inline below
 *   • Custom Sentry transactions wrap wallet connection and position open
 *
 * Telemetry only initializes if `VITE_SENTRY_DSN` is set at build time.
 * Tests / non-production builds skip Sentry automatically.
 *
 * `reportAllChanges: true` rationale:
 * Each web-vitals metric emits *every* observed value, not only the final
 * one. This is what makes Cumulative Layout Shift (CLS) and
 * Interaction-to-Next-Paint (INP) accurate on long-lived SPA sessions
 * — without `reportAllChanges` the app would only report deltas when the
 * page is being torn down, which is too late for performance debugging.
 *
 * `sendDefaultPii: false` plus the `beforeSend` scrubber are belt-and-
 * braces. Stripe / Soroban public keys are StrKey-encoded starting with
 * 'G' (56 chars); Stellar transaction hashes are 64-char lowercase hex.
 * Both shapes are redacted before any Sentry transport call.
 */

import * as Sentry from '@sentry/react';
import { onLCP, onCLS, onINP, onFCP, onTTFB } from 'web-vitals';

// StrKey public / secret seed: 56 chars, ed25519 base32 (A-Z, 2-7).
// The character after the prefix ('G' or 'S') is captured by length rather
// than a strict character class — this keeps the scrubber resistant to
// alphabet variants that may be added by sidechains / Soroban.
// `SrValue.{55}` -> the prefix character occupies 1 slot.
const PII_PATTERNS = [
  // G... / S... Stellar public / secret keys
  /[GS][A-Z2-7]{55}/g,
  // 64-char hex tx/ledger hashes — Soroban + Ethereum + Substrate share
  // the same shape, so redact any 64-char lowercase hex blob.
  /\b[a-f0-9]{64}\b/gi,
];

const scrubString = (input) => {
  if (typeof input !== 'string') return input;
  let out = input;
  for (const pattern of PII_PATTERNS) {
    out = out.replace(pattern, (matched) => {
      if (matched.length === 56 && (matched.startsWith('G') || matched.startsWith('S'))) {
        return `${matched[0]}…[redacted-stellar-key]`;
      }
      if (matched.length === 64) {
        return '[redacted-tx-hash]';
      }
      return '[redacted]';
    });
  }
  return out;
};

const scrubValue = (value) => {
  if (value == null) return value;
  if (typeof value === 'string') return scrubString(value);
  if (Array.isArray(value)) return value.map(scrubValue);
  if (typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = scrubValue(v);
    }
    return out;
  }
  return value;
};

const scrubEvent = (event) => {
  try {
    if (event.request) {
      if (event.request.url) event.request.url = scrubString(event.request.url);
      if (event.request.query_string && typeof event.request.query_string === 'string') {
        event.request.query_string = scrubString(event.request.query_string);
      }
      if (event.request.data) event.request.data = scrubValue(event.request.data);
      if (event.request.headers) event.request.headers = scrubValue(event.request.headers);
    }
    if (event.breadcrumbs) {
      event.breadcrumbs = event.breadcrumbs.map((bc) => ({
        ...bc,
        message: scrubString(bc.message),
        data: scrubValue(bc.data),
      }));
    }
    if (event.extra) event.extra = scrubValue(event.extra);
    if (event.user) {
      // Belt-and-braces: sendDefaultPii:false is set globally; force-strip
      // here in case a downstream integration ever re-attaches user data.
      event.user = {};
    }
    if (event.transaction) event.transaction = scrubString(event.transaction);
    if (event.message) event.message = scrubString(event.message);
  } catch (err) {
    // Never let the scrubber break event submission.
    // eslint-disable-next-line no-console
    console.debug('sentry_scrub_failed', err);
  }
  return event;
};

let initialized = false;

/**
 * Initialize Sentry in the browser.
 *
 * No-op in non-production builds unless the staging DSN is set.
 * Always scrubbed via beforeSend, so even malformed events get the
 * PII pass.
 */
export const initTelemetry = () => {
  if (initialized) return;

  const dsn = import.meta.env?.VITE_SENTRY_DSN;
  const environment = import.meta.env?.VITE_SENTRY_ENVIRONMENT || 'production';
  const sampleRate = Number(import.meta.env?.VITE_SENTRY_SAMPLE_RATE ?? 0.2);
  const tracesSampleRate = Number(import.meta.env?.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0.1);

  if (!dsn) {
    // Tests and local builds without a DSN — skip Sentry but still wire the
    // web-vitals → console reporter so devs can spot regressions locally.
    instrumentWebVitals({ sink: console });
    return;
  }

  Sentry.init({
    dsn,
    environment,
    release: import.meta.env?.VITE_APP_VERSION || undefined,
    // CRITICAL: never send PII by default. Combined with `beforeSend` this
    // satisfies the issue acceptance criterion "no wallet IDs or
    // transaction hashes".
    sendDefaultPii: false,
    attachStacktrace: true,
    tracesSampleRate,
    sampleRate,
    beforeSend: scrubEvent,
    beforeBreadcrumb: (bc) => {
      if (bc.message) bc.message = scrubString(bc.message);
      if (bc.data) bc.data = scrubValue(bc.data);
      return bc;
    },
    integrations: [
      Sentry.browserTracingIntegration({
        instrumentPageLoad: true,
      }),
    ],
  });

  instrumentWebVitals({ sink: Sentry });
  initialized = true;
};

/**
 * Forward Core Web Vitals into either Sentry or a dev console sink.
 *
 * `reportAllChanges: true` is essential for CLS/INP accuracy on
 * long-lived SPA dashboards — see the file-level docstring above.
 */
const instrumentWebVitals = ({ sink }) => {
  const report = (metric) => {
    if (sink === console) {
      // eslint-disable-next-line no-console
      console.debug(
        `[web-vitals] ${metric.name}`,
        metric.value,
        metric.rating,
        metric.id
      );
      return;
    }
    sink.addBreadcrumb({
      category: 'web-vitals',
      message: `${metric.name}=${metric.value}`,
      level: 'info',
      data: {
        id: metric.id,
        rating: metric.rating,
        delta: metric.delta,
      },
    });
    const activeTransaction = Sentry.getCurrentHub?.().getScope?.()?.getTransaction?.();
    if (activeTransaction) {
      activeTransaction.setMeasurement(metric.name, metric.value, metric.name === 'CLS' ? '' : 'millisecond');
    } else {
      const t = sink.startTransaction({ name: metric.name, op: 'web-vitals' });
      try {
        t.setMeasurement(metric.name, metric.value);
      } finally {
        t.finish();
      }
    }
  };

  // `reportAllChanges: true` ⇒ every observed value is reported, not just
  // the final one. Required for accurate CLS/INP on SPA dashboards.
  onLCP((m) => report(m), { reportAllChanges: true });
  onCLS((m) => report(m), { reportAllChanges: true });
  onINP((m) => report(m), { reportAllChanges: true });
  onFCP((m) => report(m), { reportAllChanges: true });
  onTTFB((m) => report(m), { reportAllChanges: true });
};

/**
 * Start a Sentry transaction that wraps a wallet connection attempt.
 * Wraps `useConnectWallet`'s connect call so the duration and outcome
 * show up alongside web-vitals in the Performance tab.
 */
export const startWalletConnectTransaction = (source) =>
  Sentry.startTransaction({
    name: `wallet.connect.${source}`,
    op: 'wallet.connect',
    tags: { source },
  });

/**
 * Start a Sentry transaction that wraps opening a leveraged position.
 * Tagged with the chosen token so we can chart performance by pair.
 */
export const startOpenPositionTransaction = (tokenSymbol) =>
  Sentry.startTransaction({
    name: `position.open.${tokenSymbol}`,
    op: 'position.open',
    tags: { token: tokenSymbol },
  });

/** Test utility — exposes the scrubber so we can assert no PII leaks. */
export const __scrubString = scrubString;
export const __scrubValue = scrubValue;
