/**
 * Quantara Soroban Transaction Utility
 *
 * Shared utilities for building, simulating, signing, and submitting
 * Soroban smart contract transactions on the Stellar network.
 *
 * This implements the standard Soroban flow:
 *   Build → Simulate → Assemble → Sign → Submit → Poll
 */

import {
  SorobanRpc,
  Contract,
  nativeToScVal,
  scValToNative,
  TransactionBuilder,
} from '@stellar/stellar-sdk';
import { getWalletPublicKey, signStellarTransaction, getNetworkPassphrase } from './wallet';
import { STELLAR_SOROBAN_RPC_URL } from '../utils/constants';

/**
 * Get a connected SorobanRPC server instance.
 */
export function getSorobanServer() {
  return new SorobanRpc.Server(STELLAR_SOROBAN_RPC_URL);
}

/**
 * Poll for a Soroban transaction result until it's complete or times out.
 *
 * @param {SorobanRpc.Server} server - The SorobanRPC server instance
 * @param {string} hash - The transaction hash to poll for
 * @param {number} maxAttempts - Maximum polling attempts (default 30 = ~30 seconds)
 * @returns {Promise<object>} The transaction result
 */
export async function pollForTransaction(server, hash, maxAttempts = 30) {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const result = await server.getTransaction(hash);
    if (result.status === 'SUCCESS') {
      return result;
    }
    if (result.status === 'FAILED') {
      throw new Error(`Soroban transaction ${hash} failed: ${result.result?.error || 'Unknown error'}`);
    }
    // Still pending — wait 1 second before retrying
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Soroban transaction ${hash} timed out after ${maxAttempts}s`);
}

/**
 * Build, simulate, sign with Freighter, and submit a Soroban contract invocation.
 *
 * This is the core Soroban flow:
 *   1. Connect to SorobanRPC
 *   2. Build the initial transaction with the Contract.call() operation
 *   3. Simulate the transaction to get footprint + resource requirements
 *   4. Assemble the final transaction from the simulation result
 *   5. Sign with Freighter
 *   6. Submit to the network
 *   7. Poll for confirmation
 *
 * @param {string} contractId - The Soroban contract ID (C... format)
 * @param {string} methodName - The contract function to call
 * @param {Array} args - Array of arguments to pass to the function
 * @returns {Promise<object>} { transaction_hash, returnValue }
 */
export async function invokeSorobanContract(contractId, methodName, args = []) {
  const publicKey = await getWalletPublicKey();
  if (!publicKey) {
    throw new Error('Wallet is not connected. Please connect your Freighter wallet first.');
  }

  const server = getSorobanServer();
  const contract = new Contract(contractId);
  const networkPassphrase = getNetworkPassphrase();

  // Convert JS arguments to Soroban ScVals
  const scValArgs = args.map((arg) => convertToScVal(arg));

  // Build the contract call operation
  const operation = contract.call(methodName, ...scValArgs);

  // Get the account for the transaction builder
  const account = await server.getAccount(publicKey);

  // Build the initial transaction (temporary — will be replaced by simulation)
  const tempTx = new TransactionBuilder(account, {
    fee: '100',
    networkPassphrase,
  })
    .addOperation(operation)
    .setTimeout(30)
    .build();

  // Simulate the transaction to get correct footprint, budget, and fees
  const simulation = await server.simulateTransaction(tempTx);

  if (!SorobanRpc.isSimulationSuccess(simulation)) {
    const errorMsg = simulation?.error || 'Unknown simulation error';
    console.error('Soroban simulation failed:', errorMsg);
    throw new Error(`Contract simulation failed: ${errorMsg}`);
  }

  // Get the assembled transaction from the simulation
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

    const returnValue = result.returnValue
      ? scValToNative(result.returnValue)
      : null;

    return {
      transaction_hash: sendResponse.hash,
      result,
      returnValue,
    };
  }

  if (sendResponse.status === 'ERROR') {
    throw new Error(`Soroban transaction submission error: ${sendResponse.errorResult?.error || 'Unknown'}`);
  }

  return {
    transaction_hash: sendResponse.hash,
    result: sendResponse,
    returnValue: null,
  };
}

/**
 * Convert a JavaScript value to the appropriate Soroban ScVal.
 *
 * Handles: strings, numbers, booleans, arrays, objects, bigint, null
 *
 * @param {*} value - The JS value to convert
 * @returns {xdr.ScVal} The Soroban ScVal
 */
function convertToScVal(value) {
  // nativeToScVal handles all common JS types natively:
  //   - string  → scvString
  //   - number  → scvI128 or scvU64 depending on range
  //   - bigint  → scvI128
  //   - boolean → scvBool
  //   - null    → scvVoid
  //   - Array   → scvVec
  //   - Uint8Array → scvBytes
  return nativeToScVal(value);
}
