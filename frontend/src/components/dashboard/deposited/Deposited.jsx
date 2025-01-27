import './deposited.css';
import EthIcon from '../../../assets/icons/ethereum.svg?react';
import StrkIcon from '../../../assets/icons/strk.svg?react';
import UsdIcon from '../../../assets/icons/usdc-icon.svg?react';

function Deposited({ data }) {
  return (
    <div className="deposited-tab-content">
      <div className="deposited-info">
        <div className="deposited-item">
          <div className="currency-name">
            <EthIcon className="icon" />
            <p>ETH</p>
          </div>
          <p className="currency-value">{data.eth}</p>
        </div>

        <div className="info-divider" />

        <div className="deposited-item">
          <div className="currency-name">
            <StrkIcon className="icon" />
            <p className="currency-name">STRK</p>
          </div>
          <p className="currency-value">{data.strk}</p>
        </div>

        <div className="info-divider" />

        <div className="deposited-item">
          <div className="currency-name">
            <UsdIcon className="icon" />
            <p className="currency-name">USDC</p>
          </div>

          <p className="currency-value">{data.usdc}</p>
        </div>

        <div className="info-divider" />

        <div className="deposited-item">
          <div className="currency-name">
            <EthIcon className="icon" />
            <p className="currency-name">USDT</p>
          </div>
          <p className="currency-value">{data.usdt}</p>
        </div>
      </div>
    </div>
  );
}

export default Deposited;
