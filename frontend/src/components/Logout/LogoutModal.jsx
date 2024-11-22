import React from "react";
import "./logoutModal.css";

export default function LogoutModal({ onClose, onLogout }) {

  return (
    <div className="modal-container">
      <div className="main-container">
        <div className="main-card">
          <div className="logout-heading-container">
            <p className="logout-heading">Logout</p>
          </div>

          <p className="logout-text">Do you want to disconnect your wallet and logout of this account?</p>
        </div>
        <div className="buttons-container">
          <button className="cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button
            className="logout-btn"
            onClick={onLogout}
          >
            Yes, logout
          </button>

        </div>
      </div>
    </div>
  );
}
