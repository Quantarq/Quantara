# Soroban Contract Deployments

This document tracks the deployment addresses for the Soroban smart contracts on Stellar networks.

## Testnet Deployments

*Network*: `https://horizon-testnet.stellar.org`
*Network Passphrase*: `Test SDF Network ; September 2015`

### Latest Deployments

| Contract | Address | Date | Commit | Notes |
|----------|---------|------|--------|-------|
| Loop     | TBA     | TBA  | TBA    | Initial Stub |
| Vault    | TBA     | TBA  | TBA    | Initial Stub |
| Rewards  | TBA     | TBA  | TBA    | Initial Stub |

## Deployment Instructions

To deploy to Testnet:

1. Build the contracts:
   ```bash
   cd quantara/soroban
   cargo build --target wasm32-unknown-unknown --release
   ```

2. Optimize contracts (optional but recommended):
   ```bash
   soroban contract optimize --wasm target/wasm32-unknown-unknown/release/loop_contract.wasm
   ```

3. Deploy using Soroban CLI:
   ```bash
   soroban contract deploy \
       --wasm target/wasm32-unknown-unknown/release/loop_contract.wasm \
       --source <your-account> \
       --network testnet
   ```

4. Update this document with the resulting contract address.
