import React, { useState, useRef, useId } from 'react';
import TokenSelector from '@/components/ui/token-selector/TokenSelector';
import BalanceCards from '@/components/ui/balance-cards/BalanceCards';
import MultiplierSelector from '@/components/ui/multiplier-selector/MultiplierSelector';
import { handleTransaction } from '@/services/transaction';
import Spinner from '@/components/ui/spinner/Spinner';
import { Button } from '@/components/ui/custom-button/Button';
import { useWalletStore } from '@/stores/useWalletStore';
import { useConnectWallet } from '@/hooks/useConnectWallet';
import { useCheckPosition } from '@/hooks/useClosePosition';
import { useNavigate } from 'react-router-dom';
import { ActionModal } from '@/components/ui/action-modal';
import { useHealthFactor } from '@/hooks/useHealthRatio';
import { notify } from '@/components/layout/notifier/Notifier';

// Error icon — non-color cue for invalid input (per #272 acceptance criterion).
const ErrorIcon = () => (
  <span
    aria-hidden="true"
    className="inline-block h-4 w-4 rounded-full bg-error text-[10px] font-bold leading-4 text-white"
  >
    !
  </span>
);

const Form = () => {
  const navigate = useNavigate();
  const { walletId, setWalletId } = useWalletStore();
  const [tokenAmount, setTokenAmount] = useState('');
  const [selectedToken, setSelectedToken] = useState('ETH');
  const [selectedMultiplier, setSelectedMultiplier] = useState('');
  const [loading, setLoading] = useState(false);

  const [isClosePositionOpen, setClosePositionOpen] = useState(false);
  // Field-level errors are now surfaced via aria-invalid + role=alert so the
  // message is announced to assistive tech without relying on red color alone.
  const [amountError, setAmountError] = useState('');
  const amountInputRef = useRef(null);
  const amountErrorId = useId();
  const amountLabelId = useId();
  const submitBtnId = useId();

  const connectWalletMutation = useConnectWallet(setWalletId);
  const { data: positionData, refetch: refetchPosition } = useCheckPosition();

  const { healthFactor, isLoading: isHealthFactorLoading } = useHealthFactor(
    selectedToken,
    tokenAmount,
    selectedMultiplier
  );

  const connectWalletHandler = () => {
    if (!walletId) {
      connectWalletMutation.mutate();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    let connectedWalletId = walletId;
    if (!connectedWalletId) {
      connectWalletHandler();
      return;
    }

    if (tokenAmount === '' || selectedToken === '' || selectedMultiplier === '') {
      const message = 'Please fill the form';
      setAmountError(message);
      notify(message, 'error');
      // Move focus to the offender so screen reader users land on the error.
      amountInputRef.current?.focus();
      return;
    }

    // Clear error before async work
    setAmountError('');

    await refetchPosition();
    if (positionData?.has_opened_position) {
      setClosePositionOpen(true);
      return;
    }

    const formData = {
      wallet_id: connectedWalletId,
      token_symbol: selectedToken,
      amount: tokenAmount,
      multiplier: selectedMultiplier,
    };
    await handleTransaction(connectedWalletId, formData, setTokenAmount, setLoading);
  };

  const handleCloseModal = () => {
    setClosePositionOpen(false);
  };

  const onClosePositionAction = () => {
    navigate('/dashboard');
  };

  const amountErrorMessageId = amountError ? amountErrorId : undefined;

  return (
    <div className="flex min-h-screen flex-col items-center gap-4 py-4">
      <BalanceCards />

      {isClosePositionOpen && (
        <ActionModal
          isOpen={isClosePositionOpen}
          title="Open New Position"
          subTitle="Do you want to open new a position?"
          content={[
            'You have already opened a position.',
            'Please close active position to open a new one.',
            "Click the 'Close Active Position' button to continue.",
          ]}
          cancelLabel="Cancel"
          submitLabel="Close Active Position"
          submitAction={onClosePositionAction}
          cancelAction={handleCloseModal}
        />
      )}
      <form
        className="text-primary flex w-full max-w-2xl flex-col justify-center gap-2.5 px-4 pb-3 sm:px-2"
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="mt-0 mb-3 text-sm font-normal sm:my-3.5 md:mb-2.5">
          <h2 className="text-center text-lg sm:text-xl">Please submit your leverage details</h2>
        </div>

        {/* Token selector — radiogroup lives inside TokenSelector itself with
            its own visible "Select Token" label, so we don't add a duplicate
            wrapper here (issue #272 review fix). */}
        <TokenSelector
          selectedToken={selectedToken}
          setSelectedToken={setSelectedToken}
          className="form-token-selector"
        />

        <div className="text-gray text-4 w-full pt-2">
          <label htmlFor={`${amountLabelId}-multiplier`}>Select Multiplier</label>
        </div>
        <div className="w-full">
          <MultiplierSelector
            id={`${amountLabelId}-multiplier`}
            setSelectedMultiplier={setSelectedMultiplier}
            selectedToken={selectedToken}
            sliderValue={selectedMultiplier}
          />
        </div>

        <div className="mt-16 mb-2 flex w-full flex-col gap-1.5">
          <label htmlFor={`${amountLabelId}-amount`} className="text-gray w-full pt-5 pb-2 text-start">
            Token Amount
          </label>
          <div className="relative w-full">
            <input
              id={`${amountLabelId}-amount`}
              ref={amountInputRef}
              className={`border-light-purple w-full [appearance:textfield] rounded-xl border bg-transparent px-6 py-5 pr-12 text-sm focus:outline-0 sm:px-8 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none ${
                amountError
                  ? 'border-error focus-visible:ring-2 focus-visible:ring-error'
                  : ''
              }`}
              type="number"
              placeholder="Enter Token Amount"
              value={tokenAmount}
              onChange={(e) => {
                setTokenAmount(e.target.value);
                if (amountError) setAmountError('');
              }}
              aria-invalid={amountError ? 'true' : 'false'}
              aria-describedby={amountErrorMessageId}
              aria-labelledby={`${amountLabelId}-amount`}
              inputMode="decimal"
            />
            {amountError && (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 right-4 -translate-y-1/2"
              >
                <ErrorIcon />
              </span>
            )}
          </div>
          {amountError && (
            <p
              id={amountErrorId}
              role="alert"
              className="text-error mt-1 flex items-center gap-1.5 text-sm"
            >
              <ErrorIcon />
              <span>{amountError}</span>
            </p>
          )}
        </div>

        <div className="w-full">
          <div className="text-gray mb-7 flex w-fit flex-row items-end gap-1.5 self-end justify-self-end sm:mb-8">
            <p>
              Estimated Health Factor Level:
              <span className="sr-only"> current value</span>
            </p>
            <p aria-live="polite">
              {isHealthFactorLoading ? 'Loading...' : healthFactor}
            </p>
          </div>
          <Button
            id={submitBtnId}
            variant="secondary"
            size="lg"
            type="submit"
            className="form-button"
            aria-busy={loading}
            disabled={loading}
          >
            {loading ? 'Submitting…' : 'Submit'}
          </Button>
        </div>
      </form>
      <Spinner loading={loading} />
    </div>
  );
};

export default Form;
