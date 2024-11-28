import React from 'react';
import { createPortal } from 'react-dom';
import './closePositionModal.css';
import { Button } from 'components/ui/Button';

export const ClosePositionModal = ({ isOpen, onClose, handleSubmit }) => {
  if (!isOpen) return null;

  return createPortal(
    <div className="close-position-overlay">
      <div className="close-position-wrapper">
        <div className="close-position-box">
          <div className="close-position-content">
            <div className="close-position-title">Open New Position</div>
            <h2>Do you want to open new a position?</h2>
            <p>You have already opened a position.</p>
            <p>Please close active position to open a new one. </p>
            <p>Click the ‘Close Active Position’ button to continue.</p>
          </div>
          <div className="close-position-actions">
            <Button variant="secondary" size="md" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" size="md" onClick={handleSubmit}>
              Close Active Position
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
