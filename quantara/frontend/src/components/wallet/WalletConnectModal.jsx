import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Button } from '@/components/ui/custom-button/Button';
import { connectWallet, disconnectWallet } from '@/services/walletconnect';
import { useWalletStore } from '@/stores/useWalletStore';

/**
 * WalletConnectModal — accessible modal that drives the WalletConnect
 * pairing flow (see Issue #273).
 *
 * - Auto-generates the QR code when the modal opens.
 * - Polls the backend via the `walletconnect` service; the polling
 *   coroutine is cancelled with an AbortController when the modal
 *   unmounts so users don't leak runaway polling.
 * - If pairing succeeds, `walletId` is set in the Zustand store and the
 *   Redis session is cleaned up on close via `disconnectWallet`.
 */
export const WalletConnectModal = ({ isOpen, onClose }) => {
  const titleId = useId();
  const descId = useId();
  const qrRef = useRef(null);
  const abortRef = useRef(null);
  const { setWalletId, walletId } = useWalletStore();
  const [status, setStatus] = useState('Preparing QR code…');
  const [submittedPk, setSubmittedPk] = useState(null);

  const runPairing = useCallback(
    async (signal) => {
      try {
        const publicKey = await connectWallet({
          qrContainer: qrRef.current,
          signal,
        });
        setSubmittedPk(publicKey);
        setWalletId(publicKey);
        try {
          localStorage.setItem('quantara_last_connected_wallet', publicKey);
        } catch {
          /* private mode / blocked storage */
        }
        setStatus('Pairing complete. You can close this window.');
      } catch (err) {
        if (err?.message === 'aborted') {
          setStatus('Pairing cancelled.');
        } else {
          setStatus(err?.message ?? 'Pairing failed.');
        }
      }
    },
    [setWalletId]
  );

  // Track the latest submittedPk through a ref so the cleanup function
  // we return below always sees the up-to-date value (closures capture
  // `submittedPk` from each render but cleanup runs once per dependency
  // change). This guarantees disconnectWallet fires after a successful
  // pairing when the modal closes.
  const submittedPkRef = useRef(null);
  useEffect(() => {
    submittedPkRef.current = submittedPk;
  }, [submittedPk]);

  // Auto-generate QR + poll when the modal opens; abort on close &
  // ensure the backend Redis session is torn down if pairing succeeded.
  useEffect(() => {
    if (!isOpen) return;
    const controller = new AbortController();
    abortRef.current = controller;
    runPairing(controller.signal);
    return () => {
      controller.abort();
      abortRef.current = null;
      // Best-effort backend teardown. disconnectWallet is noop-safe if
      // no session was established, so it can run unconditionally on
      // close without needing the latest submittedPk at this tick.
      if (submittedPkRef.current) {
        disconnectWallet().catch(() => {});
        submittedPkRef.current = null;
      }
    };
  }, [isOpen, runPairing]);

  const regenerate = async () => {
    if (abortRef.current) abortRef.current.abort();
    setStatus('Preparing QR code…');
    setSubmittedPk(null);
    if (walletId) {
      await disconnectWallet().catch(() => {});
    }
    const controller = new AbortController();
    abortRef.current = controller;
    await runPairing(controller.signal);
  };

  if (!isOpen) return null;

  const isBusy = status.startsWith('Preparing') || status.startsWith('Waiting');

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descId}
      className="fixed top-0 left-0 z-[55555] flex h-full w-full items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        data-focus-managed="true"
        className="border-nav-divider-bg bg-bg flex w-[330px] flex-col gap-4 rounded-2xl border p-6 text-white md:w-[480px]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className="border-b border-b-[rgba(255,255,255,0.1)] pb-2 text-base">
          Connect mobile wallet
        </h2>
        <p id={descId} className="text-sm opacity-80">
          Open your Stellar mobile wallet and scan the QR code to pair securely. Pairing
          expires automatically after 5 minutes.
        </p>

        <div className="flex flex-col items-center justify-center gap-3">
          <div
            className="rounded-xl border border-[#36294e] bg-[#0b0c10] p-4"
            role="img"
            aria-label="WalletConnect pairing QR code"
          >
            <canvas
              ref={qrRef}
              width={260}
              height={260}
              className="block"
              data-testid="walletconnect-qr"
            />
          </div>

          <p role="status" aria-live="polite" className="text-sm" data-testid="walletconnect-status">
            {status}
            {submittedPk && (
              <span className="sr-only"> Public key successfully paired.</span>
            )}
          </p>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="md" onClick={onClose}>
            Close
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={regenerate}
            disabled={isBusy}
            aria-busy={isBusy}
          >
            {isBusy ? 'Awaiting pairing…' : 'Regenerate QR'}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default WalletConnectModal;
