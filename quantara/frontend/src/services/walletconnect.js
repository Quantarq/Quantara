/**
 * Quantara WalletConnect Service
 *
 * Implements a WalletConnect-compatible pairing bridge for the Stellar
 * ecosystem so that mobile wallets (e.g. Lobster, StellarAuth) can connect
 * to Quantara by scanning a QR code.
 *
 * The flow mirrors the Freighter API surface (`connectWallet`,
 * `getWalletPublicKey`, `signStellarTransaction`) so consumers do not need
 * to special-case the integration.
 *
 * Acceptance criteria for Issue #273:
 *   • Stellar mobile wallet app pairs via QR code
 *   • Sign/submit path is identical to Freighter (returns XDR strings)
 *   • Pairing state is persisted via Redis with a TTL on the backend
 *
 * The URI scheme used here intentionally mirrors WalletConnect v2
 * (`wc:<topic>@<version>?symKey=<...>&relay-protocol=<...>`) so existing
 * Stellar mobile wallets that already handle wc: deep-links will route
 * automatically. The frontend never holds the private key; signing
 * happens inside the mobile wallet and the signed XDR is returned to the
 * polling endpoint.
 */
import QRCode from 'qrcode';

import { axiosInstance } from '../utils/axios';
import { STELLAR_NETWORK } from '../utils/constants';

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes — matches Redis TTL.

/**
 * A small typed cache so multiple components can ask for the currently
 * connected WalletConnect session without re-polling the backend. The
 * actual pairing state still lives in Redis; this is just a memo.
 */
const sessionCache = {
  session: /** @type {null | { session_id: string, public_key: string, uri: string }} */ (null),
  signSession: /** @type {null | { session_id: string, sub_action: string, xdr: string }} */ (null),
  activeAbort: /** @type {null | AbortController} */ (null),
};

const buildWcUri = ({ topic, version = 2, symKey, relay = 'irn' }) =>
  `wc:${topic}@${version}?symKey=${symKey}&relay-protocol=${relay}`;

const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new Error('aborted'));
      return;
    }
    const timer = setTimeout(resolve, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new Error('aborted'));
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });

const isAbortError = (err) => err && err.message === 'aborted';

/**
 * Connect to a Stellar mobile wallet through the WalletConnect-style
 * pairing bridge.
 *
 * @param {object} options
 * @param {HTMLElement} [options.qrContainer]  Element to render the QR into.
 * @param {AbortSignal} [options.signal]       Cancel polling on abort.
 * @returns {Promise<string>} The Stellar public key (G...).
 */
export const connectWallet = async ({ qrContainer, signal } = {}) => {
  // Cancel any prior in-flight poll so the previous modal session
  // doesn't leak a runaway polling coroutine (issue #273 review fix).
  if (sessionCache.activeAbort) sessionCache.activeAbort.abort();
  const controller = new AbortController();
  sessionCache.activeAbort = controller;
  const localSignal = signal ?? controller.signal;

  try {
    const pairResponse = await axiosInstance.post('/api/walletconnect/pair', {
      relay: 'irn',
      action: 'connect',
      network: STELLAR_NETWORK,
    });

    const { session_id: sessionId, uri, topic, sym_key: symKey } = pairResponse.data;
    if (!sessionId || !topic) {
      throw new Error('WalletConnect backend returned an invalid pairing envelope');
    }

    const wcUri = uri ?? buildWcUri({ topic, symKey });

    if (qrContainer) {
      QRCode.toCanvas(qrContainer, wcUri, {
        margin: 1,
        width: 280,
        color: {
          dark: '#74d6fd',
          light: '#0b0c10',
        },
      }).catch((err) => {
        if (qrContainer) qrContainer.textContent = wcUri;
        // eslint-disable-next-line no-console
        console.warn('WalletConnect QR render failed', err);
      });
    }

    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (Date.now() < deadline) {
      await sleep(POLL_INTERVAL_MS, localSignal);
      try {
        const poll = await axiosInstance.get(`/api/walletconnect/poll/${sessionId}`);
        // Axios normally throws on 4xx but some transports surface a
        // sentinel response in `poll` directly — accept both shapes for
        // easier testing via mocks.
        if (poll?.status === 404 || poll?.response?.status === 404) {
          throw new Error('Pairing session expired. Please rescan the QR code.');
        }
        const data = poll?.data ?? poll;
        if (data?.state === 'approved' && data.public_key) {
          sessionCache.session = { session_id: sessionId, public_key: data.public_key, uri: wcUri };
          return data.public_key;
        }
        if (data?.state === 'rejected') {
          throw new Error('Pairing request was rejected by the mobile wallet');
        }
        if (data?.state === 'expired') {
          throw new Error('Pairing session expired. Please rescan the QR code.');
        }
      } catch (err) {
        if (isAbortError(err)) throw err;
        if (err?.response?.status === 404) {
          throw new Error('Pairing session expired. Please rescan the QR code.');
        }
        if (err?.message?.includes('rejected') || err?.message?.includes('expired')) throw err;
        // eslint-disable-next-line no-console
        console.debug('WalletConnect poll retry', err?.message);
      }
    }

    throw new Error('Pairing timed out. Please try again.');
  } finally {
    if (sessionCache.activeAbort === controller) sessionCache.activeAbort = null;
  }
};

/**
 * Return the cached public key from a successful WalletConnect pairing.
 * Mirrors `getWalletPublicKey` in `wallet.jsx`.
 *
 * @returns {Promise<string|null>}
 */
export const getWalletPublicKey = async () => sessionCache.session?.public_key ?? null;

/**
 * Sign a Stellar transaction XDR through the active WalletConnect session.
 *
 * @param {string} xdr The base64-encoded transaction envelope.
 * @param {object} [options]
 * @param {string} [options.network] 'PUBLIC' | 'TESTNET' (defaults to env)
 * @param {AbortSignal} [options.signal]  Cancel polling on abort.
 * @returns {Promise<string>} The signed transaction XDR.
 */
export const signStellarTransaction = async (xdr, options = {}) => {
  const session = sessionCache.session;
  if (!session) {
    throw new Error('No active WalletConnect session. Please connect first.');
  }

  const subSessionResponse = await axiosInstance.post('/api/walletconnect/sign', {
    session_id: session.session_id,
    xdr,
    network: options.network ?? STELLAR_NETWORK,
  });

  const { sub_session_id: subSessionId } = subSessionResponse.data;
  if (!subSessionId) {
    throw new Error('WalletConnect backend failed to open signing sub-session');
  }
  sessionCache.signSession = { session_id: subSessionId, sub_action: 'sign', xdr };

  const localSignal = options.signal ?? new AbortController().signal;
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS, localSignal);
    try {
      const poll = await axiosInstance.get(`/api/walletconnect/poll/${subSessionId}`);
      if (poll.data?.state === 'signed' && poll.data.signed_xdr) {
        return poll.data.signed_xdr;
      }
      if (poll.data?.state === 'rejected') {
        throw new Error('Transaction signature was rejected');
      }
      if (poll.data?.state === 'expired') {
        throw new Error('Signing session expired');
      }
    } catch (err) {
      if (isAbortError(err)) throw err;
      if (err?.response?.status === 404) throw new Error('Signing session expired');
      if (err?.message?.includes('rejected') || err?.message?.includes('expired')) throw err;
    }
  }

  throw new Error('Signing timed out. Please try again.');
};

/**
 * Disconnect the active WalletConnect session — both the cached memo
 * entry and the backend Redis state.
 */
export const disconnectWallet = async () => {
  if (sessionCache.activeAbort) {
    sessionCache.activeAbort.abort();
    sessionCache.activeAbort = null;
  }
  const session = sessionCache.session;
  if (session) {
    try {
      await axiosInstance.delete(`/api/walletconnect/session/${session.session_id}`);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('WalletConnect disconnect failed (best-effort)', err?.message);
    }
  }
  sessionCache.session = null;
  sessionCache.signSession = null;
};

/**
 * Test/utility export — exposes the URI builder so unit tests can verify
 * the WalletConnect v2 envelope shape.
 */
export const __buildWcUri = buildWcUri;
