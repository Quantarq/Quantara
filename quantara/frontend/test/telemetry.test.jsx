import { describe, it, expect, beforeEach, vi } from 'vitest';
import { __scrubString, __scrubValue } from '@/services/telemetry';

// Helper: build a 56-char Stellar public key using only valid base32
// characters. Avoid counting bugs by constructing it deterministically.
const stellarKey = (filler = 'A') => `G${filler.repeat(55)}`;
const stellarSeed = (filler = 'S') => `S${filler.repeat(55)}`;
const txHash = (filler = 'a') => filler.repeat(64);

describe('privacy-safe telemetry scrubber (issue #277)', () => {
  it('redacts Stellar public keys (G…, 56 chars)', () => {
    const pubKey = stellarKey('A');
    expect(pubKey).toHaveLength(56);
    const out = __scrubString(pubKey);
    expect(out).toContain('[redacted-stellar-key]');
    expect(out).not.toBe(pubKey);
  });

  it('redacts Stellar secret seeds (S…, 56 chars)', () => {
    const seed = stellarSeed('B');
    expect(seed).toHaveLength(56);
    const out = __scrubString(seed);
    expect(out).toContain('[redacted-stellar-key]');
    expect(out).not.toBe(seed);
  });

  it('redacts a public key with realistic mixed charset', () => {
    // G + (26 letters) + (234567) + 23 chars = 56. Pulled from the real
    // Stellar base32 alphabet.
    const key =
      'GABCDEFGHIJKLMNOPQRSTUVWXYZ234567ABCDEFGHIJKLMNOPQRSTUVWXYZ2'.slice(0, 56);
    expect(key).toHaveLength(56);
    const out = __scrubString(key);
    expect(out).not.toBe(key);
    expect(out).toMatch(/\[redacted-stellar-key\]/);
  });

  it('redacts 64-char lower-hex transaction hashes', () => {
    const hash = txHash('f');
    expect(hash).toHaveLength(64);
    const out = __scrubString(`tx/${hash}`);
    expect(out).toContain('[redacted-tx-hash]');
    expect(out).not.toContain(hash);
  });

  it('redacts nested objects', () => {
    const validKey = stellarKey('A');
    const validHash = txHash('a');
    const nested = {
      request: {
        url: `https://api.example/foo?wallet_id=${validKey}`,
        data: { hash: validHash },
      },
      breadcrumbs: [
        { message: `POST /api x=${validHash}` },
      ],
    };
    const out = __scrubValue(nested);
    const json = JSON.stringify(out);
    // No raw 56-char Stellar keys anywhere in the JSON output.
    expect(json).not.toMatch(/G[A-Z2-7]{55}/);
    expect(json).not.toMatch(/S[A-Z2-7]{55}/);
    // No raw 64-char hex hashes either.
    expect(json).not.toMatch(/[a-f0-9]{64}/i);
    // The redacted markers should be present.
    expect(json).toContain('[redacted');
  });

  it('passes short non-PII strings untouched', () => {
    expect(__scrubString('hello world')).toBe('hello world');
    expect(__scrubString('https://example.com/foo')).toBe('https://example.com/foo');
  });

  it('does not throw when scrubbing weird inputs', () => {
    expect(() => __scrubValue(null)).not.toThrow();
    expect(() => __scrubValue(undefined)).not.toThrow();
    expect(__scrubValue(42)).toBe(42);
    expect(() => __scrubValue([{ hash: txHash('a') }])).not.toThrow();
    const result = __scrubValue([{ hash: txHash('a') }]);
    expect(result[0].hash).toBe('[redacted-tx-hash]');
  });
});

describe('Sentry init guarded by DSN env (issue #277)', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unmock('@sentry/react');
  });

  it('skips Sentry.init when VITE_SENTRY_DSN is unset', async () => {
    vi.doMock('@sentry/react', () => ({
      init: vi.fn(),
      startTransaction: vi.fn(),
      addBreadcrumb: vi.fn(),
      browserTracingIntegration: vi.fn(),
    }));
    const sentry = await import('@sentry/react');
    const { initTelemetry } = await import('@/services/telemetry');
    // env-less: import.meta.env.VITE_SENTRY_DSN is undefined.
    initTelemetry();
    expect(sentry.init).not.toHaveBeenCalled();
  });
});
