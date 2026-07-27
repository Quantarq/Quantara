import React, { useEffect, useState, useId } from 'react';
import { useMatchMedia } from '@/hooks/useMatchMedia';
import { getBalances } from '@/services/wallet';
import { useWalletStore } from '@/stores/useWalletStore';

import ETH from '@/assets/icons/ethereum.svg?react';
import USDC from '@/assets/icons/borrow_usdc.svg?react';
import STRK from '@/assets/icons/strk.svg?react';
import KSTRK from '@/assets/icons/kstrk.svg?react';

/**
 * BalanceCards — WCAG 2.2 AA compliant balance summary.
 *
 * Uses a definition list (`<dl>`/`<dt>`/`<dd>`) so screen readers announce
 * the token name with its balance as a related pair instead of the previous
 * implementation, which wrapped the icon inside a fake `<label>`.
 */
const BalanceCards = ({ className }) => {
  const { walletId } = useWalletStore();
  const baseId = useId();

  const isMobile = useMatchMedia('(max-width: 768px)');

  useEffect(() => {
    getBalances(walletId, setBalances);
  }, [walletId]);

  const [balances, setBalances] = useState([
    { icon: <ETH aria-hidden="true" />, title: 'ETH', balance: '0.00' },
    { icon: <USDC aria-hidden="true" />, title: 'USDC', balance: '0.00' },
    { icon: <STRK aria-hidden="true" />, title: 'STRK', balance: '0.00' },
    { icon: <KSTRK aria-hidden="true" />, title: 'kSTRK', balance: '0.00' },
  ]);

  return (
    <div
      aria-label="Token balances"
      className={`no-scrollbar mx-auto mt-3 w-full max-w-2xl overflow-x-auto px-3 ${className ?? ''}`}
    >
      <dl className="grid w-full min-w-md grid-cols-4 gap-4 rounded-[8px]">
        {balances.map((balance) => {
          const termId = `${baseId}-${balance.title}-term`;
          const defId = `${baseId}-${balance.title}-def`;
          return (
            <div
              role="group"
              aria-labelledby={termId}
              aria-describedby={defId}
              key={balance.title}
              className={`border- border-nav-divider-bg flex flex-col items-center rounded-xl border ${
                isMobile ? 'px-1 py-3' : 'px-3 py-4'
              } text-center`}
            >
              <dt id={termId} className="flex items-center gap-1 text-[#83919F]">
                <span
                  aria-hidden="true"
                  className="bg-border-color flex h-6 w-6 justify-center rounded-full p-1"
                >
                  <span className="flex h-full w-full items-center justify-center rounded-full">
                    {balance.icon}
                  </span>
                </span>
                <span className="text-sm">{balance.title} Balance</span>
              </dt>
              <dd id={defId} className="text-2xl font-semibold text-white" aria-live="polite">
                {balance.balance}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
};

export default BalanceCards;
