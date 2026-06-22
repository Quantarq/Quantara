/**
 * Quantara Soroban Contract Service
 *
 * Handles Soroban smart contract deployment and lifecycle management
 * on the Stellar network.
 *
 * Each user deploys their own instance of the leverage looping contract
 * via the Soroban RPC endpoint. The deployment follows the standard
 * Soroban flow:  Build → Simulate → Assemble → Sign → Submit → Poll
 *
 * @module contract
 */

import {
  SorobanRpc,
  Operation,
  TransactionBuilder,
  Address,
  scValToNative,
} from '@stellar/stellar-sdk';
import { getWalletPublicKey, signStellarTransaction, getNetworkPassphrase } from './wallet';
import { getSorobanServer, pollForTransaction } from './soroban';
import { SOROBAN_WASM_HASH } from '../utils/constants';
import { axiosInstance, getAuthHeaders } from '../utils/axios';
import { notify, ToastWithLink } from '../components/layout/notifier/Notifier';

/**
 * Build a Stellar Expert block explorer URL for a Soroban contract.
 *
 * @param {string} contractAddress - The Soroban contract ID (C... format)
 * @returns {string} The explorer URL
 */
const explorerContractUrl = (contractAddress) => {
  const network = process.env.VITE_STELLAR_NETWORK === 'PUBLIC' ? 'public' : 'testnet';
  return `https://stellar.expert/explorer/${network}/contract/${contractAddress}`;
};

/**
 * Deploy a Soroban smart contract for a user.
 *
 * Uses `Operation.createCustomContract` to create a contract instance
 * from a pre-installed WASM identified by its hash. The WASM hash is
 * loaded from the VITE_QUANTARA_WASM_HASH environment variable or
 * fetched from the backend /api/contract-wasm-hash endpoint.
 *
 * @param {string} walletId - The Stellar public key of the user
 * @returns {Promise<{transactionHash: string, contractAddress: string}>}
 *   Deployment result with real Soroban contract ID (C… format) and transaction hash
 */
export async function deployContract(walletId) {
  const publicKey = await getWalletPublicKey();
  if (!publicKey) {
    throw new Error('Please connect your Freighter wallet first');
  }

  console.log('Deploying Soroban contract for wallet:', walletId);

  // ------------------------------------------------------------------ //
  //  1. Resolve the WASM hash (env var → backend fallback)
  // ------------------------------------------------------------------ //
  let wasmHash = SOROBAN_WASM_HASH;
  if (!wasmHash) {
    try {
      const response = await axiosInstance.get('/api/contract-wasm-hash');
      wasmHash = response.data.wasm_hash || response.data.wasmHash;
    } catch {
      throw new Error(
        'Soroban WASM hash not configured. Set VITE_QUANTARA_WASM_HASH or ensure the backend serves /api/contract-wasm-hash.'
      );
    }
  }
  if (!wasmHash) {
    throw new Error('Soroban WASM hash is empty or not configured.');
  }

  // ------------------------------------------------------------------ //
  //  2. Connect to Soroban RPC & prepare account / salt
  // ------------------------------------------------------------------ //
  const server = getSorobanServer();
  const networkPassphrase = getNetworkPassphrase();
  const salt = crypto.getRandomValues(new Uint8Array(32));

  const account = await server.getAccount(publicKey);

  // ------------------------------------------------------------------ //
  //  3. Build the create_custom_contract operation
  // ------------------------------------------------------------------ //
  const createOp = Operation.createCustomContract({
    wasmHash,
    address: Address.fromString(publicKey),
    salt,
  });

  const tempTx = new TransactionBuilder(account, {
    fee: '100',
    networkPassphrase,
  })
    .addOperation(createOp)
    .setTimeout(30)
    .build();

  // ------------------------------------------------------------------ //
  //  4. Simulate → Assemble → Sign → Submit → Poll
  // ------------------------------------------------------------------ //

  const simulation = await server.simulateTransaction(tempTx);

  if (!SorobanRpc.isSimulationSuccess(simulation)) {
    const errorMsg = simulation?.error || 'Unknown simulation error';
    throw new Error(`Contract deployment simulation failed: ${errorMsg}`);
  }

  // Assemble the final transaction from the simulation result
  const assembledTx = simulation.transaction;

  // Sign with Freighter
  const signedXdr = await signStellarTransaction(assembledTx.toXDR(), {
    network: process.env.VITE_STELLAR_NETWORK || 'TESTNET',
  });

  // Submit the signed transaction
  const sendResponse = await server.sendTransaction(
    TransactionBuilder.fromXDR(signedXdr, networkPassphrase)
  );

  if (sendResponse.status === 'PENDING' || sendResponse.status === 'TRY_AGAIN_LATER') {
    // Poll for the result
    const result = await pollForTransaction(server, sendResponse.hash);

    // Extract the contract ID from the return value.
    // createCustomContract returns the contract address as an ScVal of type ScvAddress.
    let contractAddress;
    if (result.returnValue) {
      try {
        contractAddress = scValToNative(result.returnValue);
      } catch {
        throw new Error(
          'Deployment succeeded but could not parse the returned contract address.'
        );
      }
    } else {
      throw new Error('Deployment succeeded but no contract address was returned.');
    }

    if (!contractAddress || typeof contractAddress !== 'string') {
      throw new Error(`Invalid contract address returned: ${contractAddress}`);
    }

    console.log('Soroban contract deployed at address:', contractAddress);

    notify(
      ToastWithLink(
        'Soroban contract deployed successfully',
        explorerContractUrl(contractAddress),
        'View Contract'
      ),
      'success'
    );

    return {
      transactionHash: sendResponse.hash,
      contractAddress,
    };
  }

  if (sendResponse.status === 'ERROR') {
    throw new Error(
      `Soroban deployment submission error: ${sendResponse.errorResult?.error || 'Unknown error'}`
    );
  }

  throw new Error(`Unexpected submission status: ${sendResponse.status}`);
}

/**
 * Check if a user has a deployed contract, and deploy if not.
 *
 * This is called before creating a new position to ensure the user
 * has a contract instance deployed on the Stellar network.
 *
 * @param {string} walletId - The Stellar public key
 */
export async function checkAndDeployContract(walletId) {
  try {
    console.log('Checking if contract is deployed for wallet ID:', walletId);
    const response = await axiosInstance.get(`/api/check-user?wallet_id=${walletId}`);
    console.log('Backend response:', response.data);

    if (!response.data.is_contract_deployed) {
      console.log('Contract not deployed. Deploying...');
      const result = await deployContract(walletId);
      const contractAddress = result.contractAddress;

      console.log('Contract address:', contractAddress);

      // Update the backend with deployment info (requires wallet auth headers)
      const authHeaders = await getAuthHeaders(walletId);
      await axiosInstance.post(`/api/update-user-contract`, {
        wallet_id: walletId,
        contract_address: contractAddress,
      }, { headers: authHeaders });
      console.log('Backend updated with deployment information.');
    } else {
      console.log('Contract is already deployed for wallet ID:', walletId);
    }
  } catch (error) {
    console.error('Error checking contract status:', error);
    throw error;
  }
}
