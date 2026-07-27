import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as walletConnect from '@/services/walletconnect';

vi.mock('@/utils/axios', () => ({
  axiosInstance: {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/utils/constants', () => ({
  STELLAR_NETWORK: 'TESTNET',
}));

// Stellar public key StrKey: 'G' + 55 base32 chars (A-Z, 2-7). We use
// a deterministic 56-char fixture for tests so every assertion about
// length and pattern matches the same shape.
const BUILD_KEY = (prefix = 'G', filler = 'A') => `${prefix}${filler.repeat(55)}`;
const stellarKey56 = BUILD_KEY('G', 'A');
const stellarSeed56 = BUILD_KEY('S', 'B');
// Anchor assertions — these run at module load so a regression in the
// fixture would be caught immediately rather than per test.
expect(stellarKey56).toHaveLength(56);
expect(stellarSeed56).toHaveLength(56);
expect(stellarKey56).toMatch(/^G[A-Z2-7]{55}$/);

import { axiosInstance } from '@/utils/axios';

const pairResponse = {
  session_id: 'sess-1',
  topic: 'topic-1',
  sym_key: 'sym-1',
  uri: 'wc:topic-1@2?symKey=sym-1&relay-protocol=irn',
};

describe('walletconnect service (issue #273)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    await walletConnect.disconnectWallet().catch(() => {});
  });

  it('builds wc: URIs in the WalletConnect v2 envelope shape', () => {
    const uri = walletConnect.__buildWcUri({ topic: 'abc', symKey: 'xyz', relay: 'irn' });
    expect(uri).toBe('wc:abc@2?symKey=xyz&relay-protocol=irn');
  });

  it(
    'connectWallet polls until approved and returns the public key',
    async () => {
      axiosInstance.post.mockResolvedValueOnce({ data: pairResponse });
      axiosInstance.get
        .mockResolvedValueOnce({ data: { state: 'pending' } })
        .mockResolvedValueOnce({ data: { state: 'approved', public_key: stellarKey56 } });

      const publicKey = await walletConnect.connectWallet();
      expect(publicKey).toBe(stellarKey56);
      expect(publicKey).toMatch(/^G[A-Z2-7]{55}$/);
      expect(axiosInstance.post).toHaveBeenCalledWith(
        '/api/walletconnect/pair',
        expect.objectContaining({ action: 'connect' })
      );
      expect(await walletConnect.getWalletPublicKey()).toBe(stellarKey56);
    },
    15000
  );

  it(
    'connectWallet throws when the mobile wallet rejects the pairing',
    async () => {
      axiosInstance.post.mockResolvedValueOnce({ data: pairResponse });
      axiosInstance.get.mockResolvedValueOnce({ data: { state: 'rejected' } });
      await expect(walletConnect.connectWallet()).rejects.toThrow(/rejected/i);
    },
    15000
  );

  it(
    'connectWallet surfaces an expired session (HTTP 404 from poll)',
    async () => {
      axiosInstance.post.mockResolvedValueOnce({ data: pairResponse });
      axiosInstance.get.mockResolvedValueOnce({ status: 404, data: null });
      await expect(walletConnect.connectWallet()).rejects.toThrow(/expired/i);
    },
    15000
  );

  it('signStellarTransaction rejects when there is no active pairing session', async () => {
    await expect(walletConnect.signStellarTransaction('x')).rejects.toThrow(/connect first/i);
  });

  it(
    'signStellarTransaction opens a sub-session and returns the signed XDR',
    async () => {
      axiosInstance.post
        .mockResolvedValueOnce({ data: pairResponse })
        .mockResolvedValueOnce({ data: { sub_session_id: 'sub-1' } });
      axiosInstance.get
        .mockResolvedValueOnce({ data: { state: 'approved', public_key: stellarKey56 } })
        .mockResolvedValueOnce({ data: { state: 'signed', signed_xdr: 'signed-xdr-base64' } });

      await walletConnect.connectWallet();
      const signed = await walletConnect.signStellarTransaction('unsigned-xdr');
      expect(signed).toBe('signed-xdr-base64');
    },
    15000
  );

  it(
    'disconnectWallet clears the cache and tears down the backend session',
    async () => {
      axiosInstance.post.mockResolvedValueOnce({ data: pairResponse });
      axiosInstance.get.mockResolvedValueOnce({
        data: { state: 'approved', public_key: stellarKey56 },
      });
      await walletConnect.connectWallet();
      await walletConnect.disconnectWallet();
      expect(axiosInstance.delete).toHaveBeenCalledWith('/api/walletconnect/session/sess-1');
      expect(await walletConnect.getWalletPublicKey()).toBeNull();
    },
    15000
  );
});
