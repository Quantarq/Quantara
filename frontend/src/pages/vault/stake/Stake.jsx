import React, { useState } from 'react';
import STRK from '../../../assets/icons/strk.svg';
import USDC from '../../../assets/icons/borrow_usdc.svg';
import './stake.css';
import { VaultLayout } from '../VaultLayout';
import { CogIcon } from 'lucide-react';

function Stake() {
  const [selectedNetwork, setSelectedNetwork] = useState('Starknet');

  const networks = [{ name: 'Starknet', image: STRK }];

  const handleChange = (e) => {
    setSelectedNetwork(e.target.value);
  };
  return (
    <VaultLayout>
      <div className="staking-container">
        <div className="balance-row">
          <div className="balance-card">
            <div className="balance-card-header">
              <img src={STRK} alt="STRK" className="currency-icon" />
              <span className="balance-label">STRK Balance</span>
            </div>
            <span className="balance-amount">0.046731</span>
          </div>
          <div className="balance-card">
            <div className="balance-card-header">
              <img src={USDC} alt="APY" className="currency-icon" />
              <span className="balance-label">APY Balance</span>
            </div>
            <span className="balance-amount">0.046731</span>
          </div>
        </div>

        <h2 className="form-title">Please submit your leverage details</h2>

        <div className="staking-card">
          <div className="network-selector-container">
            <div className="network-selector">
              <div className="selected-network">
                <img
                  src={networks.find((network) => network.name === selectedNetwork)?.image}
                  alt={selectedNetwork}
                  className="network-icon"
                />
                <span>{selectedNetwork}</span>
              </div>
              <svg
                className="chevron"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M6 9L12 15L18 9"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>

            <div className="network-dropdown">
              {networks.map((network) => (
                <div key={network.name} className="network-option" onClick={() => handleChange(network)}>
                  <img src={network.image} alt={network.name} className="network-icon" />
                  <span>{network.name}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="amount-input">
            <input type="text" defaultValue="0.00" className="amount-field" />
            <span className="currency">STRK</span>
          </div>

          <div className="apy-rate">$0.00 APY / year</div>
          <hr />
          <div className="gas-fee">
            <div className="gas-icon">
              <CogIcon />
            </div>
            <div className="gas-fee-info">
              <span className="gas-text">Gas fee:</span>
              <span className="gas-amount">0.00 STRK</span>
            </div>
          </div>
        </div>

        <button className="stake-button">Stake</button>

      </div>
    </VaultLayout>
  );
}

export default Stake;
