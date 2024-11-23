import React, { useState } from 'react';
import TokenSelector from 'components/TokenSelector';
import BalanceCards from 'components/BalanceCards';
import MultiplierSelector from 'components/MultiplierSelector';
import { connectWallet } from 'services/wallet';
import { handleTransaction } from 'services/transaction';
import Spinner from 'components/spinner/Spinner';
import StarMaker from 'components/StarMaker';
import CardGradients from 'components/CardGradients';
import { ReactComponent as AlertHexagon } from 'assets/icons/alert_hexagon.svg';
import './form.css';
import { createPortal } from 'react-dom';
import useLockBodyScroll from 'hooks/useLockBodyScroll';
import CongratulationsModal from 'components/congratulationsModal/CongratulationsModal';

const Form = ({ walletId, setWalletId }) => {
  const starData = [
    { top: 35, left: 12, size: 12 },
    { top: 90, left: 7, size: 7 },
    { top: 40, left: 80, size: 7 },
    { top: 75, left: 90, size: 9 },
  ];
  const [tokenAmount, setTokenAmount] = useState('');
  const [selectedToken, setSelectedToken] = useState('');
  const [selectedMultiplier, setSelectedMultiplier] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [successful, setSuccessful] = useState(false);
  useLockBodyScroll(successful);

  const connectWalletHandler = async () => {
    try {
      setError(null);
      const address = await connectWallet();
      if (address) {
        setWalletId(address); // Correctly set the walletId using the passed setWalletId function
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

    if (tokenAmount === '' || selectedToken === '' || selectedMultiplier === '') {
      setAlertMessage('Please fill the form');
    } else {
      setAlertMessage('');
    }

    if (!connectedWalletId) {
      connectedWalletId = await connectWalletHandler();
    }

    if (connectedWalletId) {
      const formData = {
        wallet_id: connectedWalletId,
        token_symbol: selectedToken,
        amount: tokenAmount,
        multiplier: selectedMultiplier,
      };
      await handleTransaction(connectedWalletId, formData, setError, setTokenAmount, setLoading, setSuccessful);
    }
  };

  return (
    <div className="form-container">
      {successful && createPortal(<CongratulationsModal />, document.body)}
      {/* The rest of the UI stays largely unchanged */}
      <BalanceCards walletId={walletId} />
      <form onSubmit={handleSubmit}>
        <div className="form-wrapper">
          <div className="form-title">
            <h1>Please submit your leverage details</h1>
          </div>
          {alertMessage && (
            <p className="error-message form-alert">
              {alertMessage} <AlertHexagon className="form-alert-hex" />
            </p>
          )}
          <label>Select Token</label>
          <TokenSelector setSelectedToken={setSelectedToken} />
          <h5>Select Multiplier</h5>
          <MultiplierSelector setSelectedMultiplier={setSelectedMultiplier} selectedToken={selectedToken} />
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
            <button type="submit" className="form-button">
              Submit
            </button>
          </div>
          <CardGradients additionalClassName={'forms-gradient'} />
          <StarMaker starData={starData} />
        </div>
      </form>
      <Spinner loading={loading} />
    </div>
  );
};

export default Form;