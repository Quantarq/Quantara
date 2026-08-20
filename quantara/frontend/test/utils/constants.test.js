import { describe, it, expect } from 'vitest';

import { USDC_ASSET } from '../../src/utils/constants';

// The canonical testnet USDC issuer — must match
// web_app/contract_tools/constants.py's USDC_ASSET_ISSUER default
// (issue #412). The backend default is the single source of truth; this
// test guards the frontend default against drifting out of alignment.
const CANONICAL_USDC_ISSUER = 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NOJ4VBH6THS2G2V';

describe('USDC issuer consistency (issue #412)', () => {
  it('defaults to the same issuer as the backend constants', () => {
    expect(USDC_ASSET.issuer).toBe(CANONICAL_USDC_ISSUER);
  });
});
