import React, { useState, useEffect } from 'react';
import './position_history.css';
import { ReactComponent as HealthIcon } from 'assets/icons/health.svg';
import { ReactComponent as EthIcon } from 'assets/icons/ethereum.svg';
import { ReactComponent as StrkIcon } from 'assets/icons/strk.svg';
import { ReactComponent as UsdIcon } from 'assets/icons/usd_coin.svg';
import { usePositionHistoryTable } from 'hooks/usePosition';
import Spinner from 'components/spinner/Spinner';
import { formatDate } from 'utils/formatDate';
import useDashboardData from 'hooks/useDashboardData';
import Card from 'components/Card/Card';
import PositionHistoryModal from 'pages/spotnet/position_history/PositionHistoryModal';
import { useWalletStore } from 'stores/useWalletStore';

function PositionHistory() {
  const { walletId } = useWalletStore();
  const [healthFactor, setHealthFactor] = React.useState('0.00');
  const [borrowed, setBorrowed] = React.useState('0.00');
  const [selectedPosition, setSelectedPosition] = useState(null);
  const { data: tableData, isLoading } = usePositionHistoryTable(walletId);

  const { data } = useDashboardData(walletId) || {
    data: { health_ratio: '1.5', current_sum: '0.05', start_sum: '0.04', borrowed: '10.0' },
  };

  const tokenIconMap = {
    STRK: <StrkIcon className="token-icon" />,
    USDC: <UsdIcon className="token-icon" />,
    ETH: <EthIcon className="token-icon" />,
  };

  const statusStyles = {
    opened: 'status-opened',
    closed: 'status-closed',
    pending: 'status-pending',
  };

  useEffect(() => {
    const getData = async () => {
      if (isLoading || !data) {
        console.log('Card data not available');
        return;
      }

      const { health_ratio, borrowed } = data;
      console.log(data);

      setHealthFactor(health_ratio || '0.00');
      setBorrowed(borrowed || '0.00');
    };

    getData();
  }, [walletId, data, tableData, isLoading]);

  return (
    <div className="position-wrapper">
      <div className="position-container">
        <h1 className="position-title">zkLend Position History</h1>
        <div className="position-content">
          <div className="position-top-cards">
            <Card label="Health Factor" value={healthFactor} icon={<HealthIcon className="icon" />} />
            <Card label="Borrow Balance" cardData={borrowed} icon={<EthIcon className="icon" />} />
          </div>
        </div>

        <div className="position-content-table">
          <div className="position-table-title">
            <p>Position History</p>
          </div>

          <div className="position-table">
            {isLoading ? (
              <div className="spinner-container">
                <Spinner loading={isLoading} />
              </div>
            ) : (
              <table className="text-white">
                <thead>
                  <tr>
                    <th></th>
                    <th>Token</th>
                    <th>Amount</th>
                    <th>Created At</th>
                    <th>Status</th>
                    <th>Start Price</th>
                    <th>Multiplier</th>
                    <th>Liquidated</th>
                    <th>Closed At</th>
                  </tr>
                </thead>

                <tbody>
                  {tableData?.map((data, index) => (
                    <tr key={data.id}>
                      <td className="index">{index + 1}.</td>
                      <td>
                        <div className="token-cell">
                          {tokenIconMap[data.token_symbol]}
                          <span className="token-symbol">{data.token_symbol.toUpperCase()}</span>
                        </div>
                      </td>
                      <td>{Number(data.amount).toFixed(2)}</td>
                      <td>{formatDate(data.created_at)}</td>
                      <td className={`status-cell ${statusStyles[data.status.toLowerCase()] || ''}`}>
                        {data.status.charAt(0).toUpperCase() + data.status.slice(1)}
                      </td>
                      <td>{data.start_price.toFixed(2)}</td>
                      <td>{data.multiplier.toFixed(1)}</td>
                      <td>{data.is_liquidated ? 'Yes' : 'No'}</td>
                      <td>{formatDate(data.datetime_liquidation)}</td>
                      <td>
                        <span className="action-button" onClick={() => setSelectedPosition(data)}>
                          &#x22EE;
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
      {selectedPosition && (
        <PositionHistoryModal position={selectedPosition} onClose={() => setSelectedPosition(null)} />
      )}
    </div>
  );
}

export default PositionHistory;
