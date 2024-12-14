import React, { useState, useEffect } from 'react';
import { ReactComponent as ETH } from '../../assets/icons/ethereum.svg';
import { ReactComponent as USDC } from '../../assets/icons/borrow_usdc.svg';
import { ReactComponent as STRK } from '../../assets/icons/strk.svg';
import TokenSelector from 'components/TokenSelector';
import BalanceCards from 'components/BalanceCards';
import MultiplierSelector from 'components/MultiplierSelector';
import { handleTransaction } from 'services/transaction';
import Spinner from 'components/spinner/Spinner';
import { ReactComponent as AlertHexagon } from 'assets/icons/alert_hexagon.svg';
import './form.css';
import { createPortal } from 'react-dom';
import useLockBodyScroll from 'hooks/useLockBodyScroll';
import CongratulationsModal from 'components/congratulationsModal/CongratulationsModal';
import Button from 'components/ui/Button/Button';
import { useWalletStore } from 'stores/useWalletStore';
import { useConnectWallet } from 'hooks/useConnectWallet';
import { useCheckPosition } from 'hooks/useClosePosition';
import { useNavigate } from 'react-router-dom';
import { ActionModal } from 'components/ui/ActionModal';

// Token configuration
const TOKEN_CONFIG = {
  ETH: {
    id: 'ethereum',
    collateralFactor: 0.8,
    borrowFactor: 0.9,
    decimals: 18
  },
  USDC: {
    id: 'usd-coin',
    collateralFactor: 0.85,
    borrowFactor: 0.9,
    decimals: 6
  },
  STRK: {
    id: 'starknet',
    collateralFactor: 0.75,
    borrowFactor: 0.85,
    decimals: 18
  }
};

const Form = () => {
  const navigate = useNavigate();
  const { walletId, setWalletId } = useWalletStore();
  const [tokenAmount, setTokenAmount] = useState('');
  const [selectedToken, setSelectedToken] = useState('ETH');
  const [selectedMultiplier, setSelectedMultiplier] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [successful, setSuccessful] = useState(false);
  const [tokenPrice, setTokenPrice] = useState(0);
  const [healthFactor, setHealthFactor] = useState(0);
  
  useLockBodyScroll(successful);
  const [isClosePositionOpen, setClosePositionOpen] = useState(false);
  const connectWalletMutation = useConnectWallet(setWalletId);
  const { data: positionData, refetch: refetchPosition } = useCheckPosition();

  // Fetch token price from CoinGecko
  useEffect(() => {
    const fetchTokenPrice = async () => {
      try {
        const tokenId = TOKEN_CONFIG[selectedToken].id;
        const response = await fetch(
          `https://api.coingecko.com/api/v3/simple/price?ids=${tokenId}&vs_currencies=usd`
        );
        const data = await response.json();
        setTokenPrice(data[tokenId].usd);
      } catch (error) {
        console.error('Error fetching price:', error);
        setTokenPrice(0);
      }
    };

    if (selectedToken) {
      fetchTokenPrice();
    }
  }, [selectedToken]);

  // Calculate health factor whenever relevant values change
  useEffect(() => {
    const calculateHealthFactor = () => {
      if (!tokenAmount || !selectedMultiplier || !tokenPrice) {
        setHealthFactor(0);
        return;
      }

      try {
        const amount = parseFloat(tokenAmount);
        const multiplier = parseFloat(selectedMultiplier);
        
        const tokenConfig = TOKEN_CONFIG[selectedToken];
 
        const collateralValue = amount * tokenPrice * tokenConfig.collateralFactor;
        
        // Calculate borrowed amount (using multiplier)
        const borrowedAmount = amount * tokenPrice * (multiplier - 1);
        
        // Calculate debt value adjusted by borrow factor
        const adjustedDebtValue = borrowedAmount / tokenConfig.borrowFactor;
        
        // Calculate health factor
        const healthFactorValue = collateralValue / adjustedDebtValue;
        
        setHealthFactor(healthFactorValue.toFixed(6));
      } catch (error) {
        console.error('Error calculating health factor:', error);
        setHealthFactor(0);
      }
    };

    calculateHealthFactor();
  }, [tokenAmount, selectedToken, selectedMultiplier, tokenPrice]);

  const connectWalletHandler = () => {
    if (!walletId) {
      connectWalletMutation.mutate();
    }
  };

  const [balances, setBalances] = useState([
    { icon: <ETH />, title: 'ETH', balance: '0.00' },
    { icon: <USDC />, title: 'USDC', balance: '0.00' },
    { icon: <STRK />, title: 'STRK', balance: '0.00' },
  ]);

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
      setAlertMessage('Please fill the form');
      return;
    }

    setAlertMessage('');

    const formData = {
      wallet_id: connectedWalletId,
      token_symbol: selectedToken,
      amount: tokenAmount,
      multiplier: selectedMultiplier,
    };
    await handleTransaction(connectedWalletId, formData, setError, setTokenAmount, setLoading, setSuccessful);
  };

  const handleCloseModal = () => {
    setClosePositionOpen(false);
  };

  const onClosePositionAction = () => {
    navigate('/dashboard');
  };

  return (
    <div className="form-content-wrapper">
      <BalanceCards balances={balances} setBalances={setBalances} walletId={walletId} />
      {successful && createPortal(<CongratulationsModal />, document.body)}
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
      <form className="form-container" onSubmit={handleSubmit}>
        <div className="form-title">
          <h1>Please submit your leverage details</h1>
        </div>
        {alertMessage && (
          <p className="error-message form-alert">
            {alertMessage} <AlertHexagon className="form-alert-hex" />
          </p>
        )}
        <label className="token-select">Select Token</label>
        <TokenSelector selectedToken={selectedToken} setSelectedToken={setSelectedToken} />
        <label>Select Multiplier</label>
        <MultiplierSelector
          setSelectedMultiplier={setSelectedMultiplier}
          selectedToken={selectedToken}
          sliderValue={selectedMultiplier}
        />
        <div className="token-label">
          <label className="token-amount">Token Amount</label>
          {error && <p className="error-message">{error}</p>}
          <input
            type="number"
            placeholder="Enter Token Amount"
            value={tokenAmount}
            onChange={(e) => setTokenAmount(e.target.value)}
            className={error ? 'error' : ''}
          />
        </div>
        <div>
          <div className="form-health-factor">
            <p>
              Estimated Health Factor Level:
            </p>
            <p>
              {healthFactor || 0}
            </p>
          </div>
          <div className="form-button-container">
            <Button variant="secondary" size="lg" type="submit">
              Submit
            </Button>
          </div>
        </div>
      </form>
      <Spinner loading={loading} />
    </div>
  );
};

export default Form;