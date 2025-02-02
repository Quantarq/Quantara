import React, { useEffect, useState } from 'react';
import { useMatchMedia } from '@/hooks/useMatchMedia';
import { getBalances } from '@/services/wallet';
import { useWalletStore } from '@/stores/useWalletStore';

import ETH from '@/assets/icons/ethereum.svg';
import USDC from '@/assets/icons/borrow_usdc.svg';
import STRK from '@/assets/icons/strk.svg';

const BalanceCards = ({ className }) => {
  const { walletId } = useWalletStore();

  const isMobile = useMatchMedia('(max-width: 768px)');

  useEffect(() => {
    getBalances(walletId, setBalances);
  }, [walletId]);

  const [balances, setBalances] = useState([
    { icon: ETH, title: 'ETH', balance: '0.00' },
    { icon: USDC, title: 'USDC', balance: '0.00' },
    { icon: STRK, title: 'STRK', balance: '0.00' },
  ]);

  return (
    <div className="mt-3 mx-auto max-w-2xl px-3 w-full overflow-x-auto no-scrollbar">
      <div className="grid grid-cols-3 w-full rounded-[8px] gap-5  min-w-md">
        {balances.map((balance) =>
          isMobile ? (
            <div
              className="border flex flex-col items-center text-center border- py-3 rounded-xl border-nav-divider-bg px-1"
              key={balance.title}
            >
              <label htmlFor={balance.title} className={'flex text-[#83919F] gap-1 items-center'}>
                <div className="h-6 w-6 rounded-full bg-border-color flex justify-center p-1">
                  <img src={balance.icon} className="w-full h-full" />
                </div>
                <span className="text-sm">{balance.title} Balance</span>
              </label>
              <label htmlFor={balance.title}>
                <span className="font-semibold text-2xl text-white">{balance.balance}</span>
              </label>
            </div>
          ) : (
            <div
              className="border flex flex-col items-center text-center border- py-4 px-6 rounded-xl border-nav-divider-bg "
              key={balance.title}
            >
              <label htmlFor={balance.title} className={'flex text-[#83919F] gap-1'}>
                <div className="h-6 w-6 rounded-full bg-border-color flex justify-center p-1">
                  <img src={balance.icon} className="w-full h-full" />
                </div>
                <span className="">{balance.title} Balance</span>
              </label>
              <label htmlFor={balance.title}>
                <span className="font-semibold text-2xl text-white">{balance.balance}</span>
              </label>
            </div>
          )
        )}
      </div>
    </div>
  );
};

export default BalanceCards;
