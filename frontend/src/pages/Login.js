import React from 'react';

function Login({ onConnectWallet }) {
  return (
    <div className='form-container'>
      <h2>Connect Your Wallet</h2>
      <button className='btn-submit' onClick={onConnectWallet}>
        Connect Wallet
      </button>
    </div>
  );
}

export default Login;
