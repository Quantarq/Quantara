import React, { useState } from 'react';
import TokenSelector from '@/components/ui/token-selector/TokenSelector';
import BalanceCards from '@/components/ui/balance-cards/BalanceCards';
import MultiplierSelector from '@/components/ui/multiplier-selector/MultiplierSelector';
import { handleTransaction } from '@/services/transaction';
import Spinner from '@/components/ui/spinner/Spinner';
import './form.css';
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
    <div className="flex flex-col gap-[30px] justify-start items-center py-4 min-h-screen md:gap-0">
      <BalanceCards className="balance-card" />

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
      <form className="flex justify-center flex-col gap-[10px] pb-[60px] w-[626px] text-primary md:mx-0 md:p-4 md:w-full " onSubmit={handleSubmit}>
        <div className="form-title md:px-4 text-center font-normal text-xl mb-[10px] md:text-base">
          <h1>Please submit your leverage details</h1>
        </div>

        <TokenSelector
          selectedToken={selectedToken}
          setSelectedToken={setSelectedToken}
          className="form-token-selector md:px-4"
        />
        <label className='md:px-4 md:text-xs text-base text-gray'>Select Multiplier</label>
        <MultiplierSelector
          setSelectedMultiplier={setSelectedMultiplier}
          selectedToken={selectedToken}
          sliderValue={selectedMultiplier}
        />
        <div className="flex flex-col gap-[5px] mt-[60px] md:px-4 md:mt-0">
          <label className="md:mt-[25px] mt-5 mb-3">Token Amount</label>
          <input
          className='bg-transparent md:rounded-2xl md:text-sm rounded-[50px] py-5 px-[30px] text-gray border border-' //light purpule
            type="number"
            placeholder="Enter Token Amount"
            value={tokenAmount}
            onChange={(e) => setTokenAmount(e.target.value)}
          />
        </div>
        <div>
          <div className="flex items-end justify-self-end w-fit m-[2px] text-gray self-end gap-[5px] md:px-4">
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
