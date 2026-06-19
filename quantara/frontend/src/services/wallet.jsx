/**
 * Quantara Stellar Wallet Service
 *
 * Handles wallet connections using the Stellar Freighter browser extension
 * and the Stellar SDK for account operations.
 *
 * Replaces the former Starknet/starknetkit wallet integration.
 *
 * @module wallet
 */
import { useWalletStore } from '../stores/useWalletStore';
import {
  requestAccess,
  isConnected,
  getPublicKey,
  signTransaction,
} from '@stellar/freighter-api';
import { StrKey } from '@stellar/stellar-sdk';

import { XLM_ASSET, USDC_ASSET } from '../utils/constants';

/**
 * Check if Freighter is installed in the browser.
 *
 * @returns {boolean} True if Freighter wallet extension is available
 */
export const isFreighterInstalled = () => {
  try {
    return window?.freighter?.isConnected !== undefined || isConnected();
  } catch {
    return false;
  }
};

/**
 * Connect to Freighter wallet.
 * Prompts the user to connect their wallet via the Freighter browser extension.
 *
 * @returns {Promise<string>} The user's Stellar public key
 * @throws {Error} If connection fails or Freighter is not installed
 */
export const connectWallet = async () => {
  try {
    console.log('Connecting to Freighter wallet...');

    if (!isFreighterInstalled()) {
      throw new Error(
        'Freighter wallet is not installed. Please install the Freighter browser extension from https://freighter.app'
      );
    }

    const publicKey = await requestAccess();

    if (!publicKey || !StrKey.isValidEd25519PublicKey(publicKey)) {
      throw new Error('Invalid Stellar public key received from wallet');
    }

    console.log('Wallet connected successfully. Public key:', publicKey);
    return publicKey;
  } catch (error) {
    console.error('Error connecting wallet:', error.message);
    throw error;
  }
};

/**
 * Get the current wallet public key without prompting.
 *
 * @returns {Promise<string|null>} The public key or null if not connected
 */
export const getWalletPublicKey = async () => {
  try {
    const connected = await isConnected();
    if (!connected) return null;

    const publicKey = await getPublicKey();
    return publicKey || null;
  } catch {
    return null;
  }
};

/**
 * Disconnect wallet (clears local state).
 * Note: Freighter doesn't have a programmatic disconnect, so we just clear local state.
 */
export function logout() {
  localStorage.removeItem('wallet_id');
  localStorage.removeItem('quantara_last_connected_wallet');
}

/**
 * Sign a Stellar transaction XDR using Freighter.
 *
 * @param {string} xdr - The base64-encoded transaction XDR string
 * @param {object} options - Signing options
 * @param {string} [options.network='TESTNET'] - Network to use ('PUBLIC' | 'TESTNET')
 * @returns {Promise<string>} The signed transaction XDR
 */
/**
 * Sign a Stellar transaction XDR using Freighter.
 *
 * @param {string} xdr - The base64-encoded transaction XDR string
 * @param {object} options - Signing options
 * @param {string} [options.network='TESTNET'] - Network to use ('PUBLIC' | 'TESTNET')
 * @returns {Promise<string>} The signed transaction XDR
 */
export const signStellarTransaction = async (xdr, options = { network: 'TESTNET' }) => {
  try {
    const signedXDR = await signTransaction(xdr, options);
    return signedXDR;
  } catch (error) {
    console.error('Error signing transaction:', error);
    throw error;
  }
};

/**
 * Get the network passphrase for the configured Stellar network.
 *
 * @param {string} [network] - 'TESTNET' or 'PUBLIC' (defaults to env var or TESTNET)
 * @returns {string} The Stellar network passphrase
 */
export const getNetworkPassphrase = (network = process.env.VITE_STELLAR_NETWORK || 'TESTNET') => {
  const networks = {
    PUBLIC: 'Public Global Stellar Network ; September 2015',
    TESTNET: 'Test SDF Network ; September 2015',
    FUTURENET: 'Test SDF Future Network ; October 2022',
  };
  return networks[network] || networks.TESTNET;
};

/**
 * Get Stellar token balances for the connected wallet.
 * Uses the Stellar Horizon API to load account and extract balances.
 *
 * @param {string} publicKey - The Stellar public key
 * @returns {Promise<Object>} Token balances keyed by symbol
 */
/**
 * Get Stellar token balances for the connected wallet.
 * Uses the Stellar Horizon API to load account and extract balances.
 *
 * @param {string} publicKey - The Stellar public key
 * @returns {Promise<Object>} Token balances keyed by symbol
 */
export async function getTokenBalances(publicKey) {
  try {
    const { Server } = await import('@stellar/stellar-sdk');
    const horizonUrl =
      process.env.VITE_STELLAR_HORIZON_URL || 'https://horizon-testnet.stellar.org';
    const server = new Server(horizonUrl);
    const account = await server.loadAccount(publicKey);

    const balances = {
      XLM: '0.0000',
      USDC: '0.0000',
    };

    for (const balance of account.balances) {
      if (balance.asset_type === 'native') {
        balances.XLM = parseFloat(balance.balance).toFixed(4);
      } else if (
        balance.asset_code === USDC_ASSET.code &&
        balance.asset_issuer === USDC_ASSET.issuer
      ) {
        balances.USDC = parseFloat(balance.balance).toFixed(4);
      }
    }

    return balances;
  } catch (error) {
    console.error('Error fetching token balances:', error);
    // Return zeros if account doesn't exist on network yet
    return { XLM: '0.0000', USDC: '0.0000' };
  }
}

/**
 * Fetch and format token balances for display in the UI.
 *
 * @param {string} walletId - The Stellar public key
 * @param {Function} setBalances - React state setter for the balances array
 * @returns {Promise<void>}
 */
export const getBalances = async (walletId, setBalances) => {
  if (!walletId) return;
  try {
    const data = await getTokenBalances(walletId);

    const updatedBalances = [
      {
        icon: null, // Will be populated via icon components
        title: 'XLM',
        balance: data.XLM !== undefined ? data.XLM.toString() : '0.0000',
      },
      {
        icon: null,
        title: 'USDC',
        balance: data.USDC !== undefined ? data.USDC.toString() : '0.0000',
      },
    ];

    setBalances(updatedBalances);
  } catch (error) {
    console.error('Error fetching user balances:', error);
  }
};

export const disconnectWallet = async () => {
  try {
    // 1. Alert the backend to delete the secure httpOnly cookie
    await axios.post('/api/auth/logout');
  } catch (error) {
    console.error('Failed to cleanly terminate wallet session on backend:', error);
  } finally {
    // 2. Clear state elements out of application memory regardless of network success
    useWalletStore.getState().clearWallet();
  }
};