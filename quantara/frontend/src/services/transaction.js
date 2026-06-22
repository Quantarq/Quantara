/**
 * Quantara Transaction Service
 *
 * Handles Stellar/Soroban transaction building, signing, and submission.
 * Uses the Soroban SDK pattern: Build → Simulate → Assemble → Sign → Submit → Poll.
 *
 * All transactions are Soroban smart contract invocations signed via Freighter.
 */

import { getWalletPublicKey } from './wallet';
import { invokeSorobanContract } from './soroban';
import { axiosInstance, getAuthHeaders } from '../utils/axios';
import { notify, ToastWithLink } from '../components/layout/notifier/Notifier';
import { STELLAR_NETWORK } from '../utils/constants';

/**
 * Build a Stellar Explorer URL for a transaction hash,
 * automatically selecting the correct network (testnet/mainnet).
 */
const explorerTxUrl = (hash) =>
  `https://stellar.expert/explorer/${STELLAR_NETWORK === 'PUBLIC' ? 'public' : 'testnet'}/tx/${hash}`;

/**
 * Build and send a Soroban loop_liquidity transaction.
 *
 * Invokes the Quantara Soroban contract's loop_liquidity function to
 * create a new leveraged position via the deposit-borrow-swap-redeposit loop.
 *
 * @param {object} loopData - The loop liquidity data from the backend
 * @param {string} contractAddress - The user's Soroban contract address
 * @returns {Promise<{transaction_hash: string}>}
 */
export async function sendTransaction(loopData, contractAddress) {
  try {
    const publicKey = await getWalletPublicKey();
    if (!publicKey) {
      throw new Error('Wallet is not connected');
    }

    console.log('Sending loop_liquidity Soroban call:', {
      contractAddress,
      loopData,
    });

    const { transaction_hash, result } = await invokeSorobanContract(
      contractAddress,
      'loop_liquidity',
      [
        loopData.deposit_data.token,         // deposit_token (string)
        loopData.deposit_data.amount,         // amount (string/number)
        loopData.deposit_data.multiplier,     // multiplier (number)
        loopData.pool_key?.token1,            // borrow_token (optional)
      ]
    );

    console.log('loop_liquidity transaction complete:', transaction_hash);

    notify(
      ToastWithLink(
        'Position created successfully',
        explorerTxUrl(transaction_hash),
        'View Transaction'
      ),
      'success'
    );

    return { transaction_hash };
  } catch (error) {
    console.error('Error sending loop_liquidity transaction:', error);
    throw error;
  }
}

/**
 * Close a leveraged position via the Soroban contract.
 *
 * Invokes close_position on the Quantara contract to repay debt,
 * withdraw collateral, and close the position.
 *
 * @param {object} transactionData - Close position data from the backend
 * @returns {Promise<{transaction_hash: string}>}
 */
export async function closePosition(transactionData) {
  try {
    const publicKey = await getWalletPublicKey();
    if (!publicKey) {
      throw new Error('Wallet is not connected');
    }

    console.log('Closing position:', transactionData);

    const { transaction_hash } = await invokeSorobanContract(
      transactionData.contract_address,
      'close_position',
      [
        transactionData.supply_token,   // supply_token address
        transactionData.debt_token,     // debt_token address
        transactionData.repay_const || 93,  // repay percentage
      ]
    );

    console.log('close_position transaction:', transaction_hash);

    notify(
      ToastWithLink(
        'Position closed successfully',
        explorerTxUrl(transaction_hash),
        'View Transaction'
      ),
      'success'
    );

    return { transaction_hash };
  } catch (error) {
    console.error('Error closing position:', error);
    throw error;
  }
}

/**
 * Send an extra deposit transaction to add collateral to an existing position.
 *
 * Invokes extra_deposit on the Quantara Soroban contract.
 *
 * @param {object} depositData - Extra deposit parameters
 *   @param {string} depositData.token_address - The asset to deposit
 *   @param {string} depositData.token_amount - Amount to deposit
 * @param {string} userContractAddress - The user's Soroban contract address
 * @returns {Promise<{transaction_hash: string}>}
 */
export async function sendExtraDepositTransaction(depositData, userContractAddress) {
  try {
    const publicKey = await getWalletPublicKey();
    if (!publicKey) {
      throw new Error('Wallet is not connected');
    }

    console.log('Sending extra_deposit:', { depositData, userContractAddress });

    const { transaction_hash } = await invokeSorobanContract(
      userContractAddress,
      'extra_deposit',
      [
        depositData.token_address,   // token address
        depositData.token_amount,    // amount
      ]
    );

    console.log('extra_deposit transaction:', transaction_hash);

    notify(
      ToastWithLink(
        'Extra deposit submitted successfully',
        explorerTxUrl(transaction_hash),
        'View Transaction'
      ),
      'success'
    );

    return { transaction_hash };
  } catch (error) {
    console.error('Error sending extra deposit transaction:', error);
    throw error;
  }
}

/**
 * Send a withdraw-all transaction to fully exit a position.
 *
 * Invokes close_position followed by withdraw on the Quantara Soroban contract
 * to close the leveraged position and withdraw all remaining collateral.
 *
 * @param {object} data - Withdraw data from the backend
 *   @param {object} data.repay_data - Close position parameters
 *   @param {Array} data.tokens - Tokens to withdraw after closing
 * @param {string} userContractAddress - The user's Soroban contract address
 * @returns {Promise<{transaction_hash: string}>}
 */
export async function sendWithdrawAllTransaction(data, userContractAddress) {
  try {
    const publicKey = await getWalletPublicKey();
    if (!publicKey) {
      throw new Error('Wallet is not connected');
    }

    console.log('Sending withdraw-all:', { data, userContractAddress });

    // Step 1: Close the position
    const closeResult = await invokeSorobanContract(
      userContractAddress,
      'close_position',
      [
        data.repay_data.supply_token,
        data.repay_data.debt_token,
        data.repay_data.repay_const || 93,
      ]
    );

    console.log('close_position done:', closeResult.transaction_hash);

    // Step 2: Withdraw each token
    const withdrawResults = [];
    for (const token of data.tokens || []) {
      const withdrawResult = await invokeSorobanContract(
        userContractAddress,
        'withdraw',
        [
          token.address || token,   // token address
          0,                         // amount (0 = withdraw all)
        ]
      );
      withdrawResults.push(withdrawResult);
    }

    console.log('Withdraw-all complete', {
      closeHash: closeResult.transaction_hash,
      withdrawHashes: withdrawResults.map((r) => r.transaction_hash),
    });

    notify(
      ToastWithLink(
        'Withdraw all complete',
        explorerTxUrl(closeResult.transaction_hash),
        'View Transaction'
      ),
      'success'
    );

    return {
      transaction_hash: closeResult.transaction_hash,
    };
  } catch (error) {
    console.error('Error sending withdraw transaction', error);
    throw error;
  }
}

/**
 * Main handler for creating a leveraged position.
 *
 * Orchestrates full lifecycle: check wallet, get backend data,
 * invoke the Soroban contract, and notify the backend.
 *
 * @param {string} connectedWalletId - The Stellar public key
 * @param {object} formData - Position creation form data
 * @param {function} setTokenAmount - State setter to reset form
 * @param {function} setLoading - State setter for loading state
 */
export const handleTransaction = async (connectedWalletId, formData, setTokenAmount, setLoading) => {
  setLoading(true);
  try {
    const publicKey = await getWalletPublicKey();
    if (!publicKey) {
      notify('Please connect your Freighter wallet first', 'error');
      setLoading(false);
      return;
    }

    // Get position data from backend (requires wallet auth headers)
    const authHeaders = await getAuthHeaders(connectedWalletId);
    const response = await axiosInstance.post(`/api/create-position`, formData, { headers: authHeaders });
    const transactionData = response.data;

    console.log('Position data received:', transactionData);

    // Invoke Soroban loop_liquidity contract
    const { transaction_hash } = await sendTransaction(
      transactionData,
      transactionData.contract_address
    );

    // Notify backend of position creation with real transaction hash
    await axiosInstance.get(`/api/open-position`, {
      params: {
        position_id: transactionData.position_id,
        transaction_hash,
      },
    });

    setTokenAmount('');
  } catch (err) {
    console.error('Failed to create position:', err);
    notify(`Error: ${err.message || 'Failed to create position'}`, 'error');
  } finally {
    setLoading(false);
  }
};
