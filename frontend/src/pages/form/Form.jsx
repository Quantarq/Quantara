import React, { useState } from 'react';
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

const Form = () => {
  const navigate = useNavigate();
  const { walletId, setWalletId } = useWalletStore();
  const [tokenAmount, setTokenAmount] = useState('');
  const [selectedToken, setSelectedToken] = useState('ETH');
  const [selectedMultiplier, setSelectedMultiplier] = useState('');
  const [loading, setLoading] = useState(false);

  const [isClosePositionOpen, setClosePositionOpen] = useState(false);
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

    await refetchPosition();
    if (positionData?.has_opened_position) {
      setClosePositionOpen(true);
      return;
    }

    if (tokenAmount === '' || selectedToken === '' || selectedMultiplier === '') {
      notify('Please fill the form', 'error');
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

  return (
    <div className="flex flex-col gap-4 items-center py-4 min-h-screen">
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
        className="flex justify-center px-4 flex-col gap-2.5 pb-3  max-w-2xl w-full text-primary sm:px-2"
        onSubmit={handleSubmit}
      >
        <div className=" font-normal text-sm md:mb-2.5 mt-0 mb-3 sm:my-3.5">
          <h2 className="text-lg sm:text-xl text-center">Please submit your leverage details</h2>
        </div>
        <TokenSelector
          selectedToken={selectedToken}
          setSelectedToken={setSelectedToken}
          className="form-token-selector"
        />
        <div className="text-gray text-4 w-full pt-2">
          <label>Select Multiplier</label>
        </div>
        <div className="w-full">
          <MultiplierSelector
            setSelectedMultiplier={setSelectedMultiplier}
            selectedToken={selectedToken}
            sliderValue={selectedMultiplier}
          />
        </div>
        <div className="flex flex-col gap-1.5 mt-16 w-full mb-2">
          <label className="text-start w-full text-gray pt-5 pb-2 ">Token Amount</label>
          <input
            className="rounded-xl text-sm bg-transparent py-5 px-6 sm:px-8 border-light-purple border w-full focus:outline-0 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            type="number"
            placeholder="Enter Token Amount"
            value={tokenAmount}
            onChange={(e) => setTokenAmount(e.target.value)}
          />
        </div>
        <div className="w-full">
          <div className="flex flex-row items-end justify-self-end w-fit mb-7 sm:mb-8 text-gray gap-1.5 self-end">
            <p>Estimated Health Factor Level:</p>
            <p>{isHealthFactorLoading ? 'Loading...' : healthFactor}</p>
          </div>
          <Button variant="secondary" size="lg" type="submit" className="form-button">
            Submit
          </Button>
        </div>
      </form>
      <Spinner loading={loading} />
    </div>
  );
};

export default Form;
