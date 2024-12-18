import React from 'react';
import './position_history.css';
import { formatDate } from 'utils/formatDate';

function PositionHistoryModal({ position, onClose }) {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <p>
            <span>
              {position.token_symbol} {Number(position.amount).toFixed(2)}
            </span>
            <span className={`status-${position.status.toLowerCase()}`}>
              {position.status.charAt(0).toUpperCase() + position.status.slice(1)}
            </span>
          </p>

          <button onClick={onClose} className="close-button">
            X
          </button>
        </div>
        <div className="modal-body">
          <div className="detail-row">
            <p>
              Start Price: <span>{position.start_price.toFixed(2)}</span>
            </p>
          </div>
          <div className="detail-row">
            <p>
              Multiplier: <span>{position.multiplier.toFixed(1)}</span>
            </p>
          </div>
          <div className="detail-row">
            <p>
              Liquidated: <span>{position.is_liquidated ? 'Yes' : 'No'}</span>
            </p>
          </div>
          <div className="detail-row">
            <p>
              Created At: <span>{formatDate(position.created_at)}</span>
            </p>
          </div>
          <div className="detail-row">
            <p>
              Closed At: <span>{formatDate(position.datetime_liquidation)}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PositionHistoryModal;
