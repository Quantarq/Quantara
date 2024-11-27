import BalanceCards from 'components/BalanceCards';
import MultiplierSelector from 'components/MultiplierSelector';
import Spinner from 'components/spinner/Spinner';
import TokenSelector from 'components/TokenSelector';
import { useState } from 'react';
import { handleTransaction } from 'services/transaction';
import { connectWallet } from 'services/wallet';

// import StarMaker from 'components/StarMaker';
import CardGradients from 'components/CardGradients';
import ClosePositionModal from 'components/modals/ClosePositionModal';

import { ReactComponent as AlertHexagon } from 'assets/icons/alert_hexagon.svg';
import CongratulationsModal from 'components/congratulationsModal/CongratulationsModal';
import { useCheckPosition } from 'hooks/useClosePosition';
import useLockBodyScroll from 'hooks/useLockBodyScroll';
import { createPortal } from 'react-dom';
import './form.css';
const Form = ({ walletId, setWalletId }) => {
  const [tokenAmount, setTokenAmount] = useState('');
  const [selectedToken, setSelectedToken] = useState('ETH');
  const [selectedMultiplier, setSelectedMultiplier] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [successful, setSuccessful] = useState(false);
  useLockBodyScroll(successful);
  const [isPositionModalOpened, setIsPositionModalOpened] = useState(false);
  const { data: positionData, refetch } = useCheckPosition(walletId);

  const connectWalletHandler = async () => {
    try {
      setError(null);
      const address = await connectWallet();
      if (address) {
        setWalletId(address);
        console.log('Wallet successfully connected. Address:', address);
        return address;
      } else {
        setError('Failed to connect wallet. Please try again.');
        console.error('Wallet connection flag is false after enabling');
      }
    } catch (error) {
      console.error('Wallet connection failed:', error);
      setError('Failed to connect wallet. Please try again.');
    }
    return null;
  };
  const handleSubmit = async (e) => {
    e.preventDefault();

    let connectedWalletId = walletId;
    if (!connectedWalletId) {
      connectedWalletId = await connectWalletHandler();
      if (!connectedWalletId) return;
    }
    await refetch();
    if (positionData?.has_opened_position) {
      setIsPositionModalOpened(true);
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
  const handleClosePosition = () => {
    setIsPositionModalOpened(false);
    window.location.href = '/dashboard';
  };
  return (
    <div className="form-container">
      {successful && createPortal(<CongratulationsModal />, document.body)}

      {/* The rest of the UI stays largely unchanged */}
      <BalanceCards walletId={walletId} />
      <form onSubmit={handleSubmit}>
        <div className="form-wrapper">
          <div className="form-title">
            <h1 className="">Please submit your leverage details</h1>
          </div>
          {alertMessage && (
            <p className="error-message form-alert">
              {alertMessage} <AlertHexagon className="form-alert-hex" />
            </p>
          )}
          <label>Select Token</label>
          <TokenSelector currentToken={selectedToken} setSelectedToken={setSelectedToken} />
          <h5 className="select-multiplier">Select Multiplier</h5>
          <MultiplierSelector
            defaultValue={4}
            setSelectedMultiplier={setSelectedMultiplier}
            selectedToken={selectedToken}
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
            <button type="submit" className="form-button">
              Submit
            </button>
          </div>
          <CardGradients additionalClassName={'forms-gradient'} />
          {/* <StarMaker starData={starData} /> */}
        </div>
      </form>
      <ClosePositionModal
        text={
          " You have already opened a position. Please close active position to open a new one. Click the 'Close Active Position' button to continue."
        }
        actionText={'  Do you want to open new a position?'}
        header={'Open New Position'}
        isOpen={isPositionModalOpened}
        onClose={() => setIsPositionModalOpened(false)}
        closePosition={handleClosePosition}
      />
      <Spinner loading={loading} />

      <div className="form-content-wrapper">
        <BalanceCards walletId={walletId} />
        {successful && createPortal(<CongratulationsModal />, document.body)}
        <StyledPopup
          isOpen={isPositionModalOpened}
          onClose={() => setIsPositionModalOpened(false)}
          onClosePosition={handleClosePosition}
        />

        {/* The rest of the UI stays largely unchanged */}
        <form className="form-container" onSubmit={handleSubmit}>
          <div className="form-title">
            <h1>Please submit your leverage details</h1>
          </div>
          {alertMessage && (
            <p className="error-message form-alert">
              {alertMessage} <AlertHexagon className="form-alert-hex" />
            </p>
          )}
          <label>Select Token</label>
          <TokenSelector selectedToken={selectedToken} setSelectedToken={setSelectedToken} />
          <label>Select Multiplier</label>
          <MultiplierSelector
            setSelectedMultiplier={setSelectedMultiplier}
            selectedToken={selectedToken}
            sliderValue={selectedMultiplier}
          />
          <div className="token-label">
            <label>Token Amount</label>
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
            <div className="form-button-container">
              <button type="submit" className="form-button">
                Submit
              </button>
            </div>
          </div>
        </form>
        <Spinner loading={loading} />
      </div>
    </div>
  );
};

export default Form;
