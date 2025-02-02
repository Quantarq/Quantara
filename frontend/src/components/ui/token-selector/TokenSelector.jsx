import React from 'react';
import ETH from '@/assets/icons/ethereum.svg?react';
import USDC from '@/assets/icons/borrow_usdc.svg?react';
import STRK from '@/assets/icons/strk.svg?react';

const Tokens = [
  { id: 'ethOption', component: <ETH />, label: 'ETH' },
  { id: 'usdcOption', component: <USDC />, label: 'USDC' },
  { id: 'strkOption', component: <STRK />, label: 'STRK' },
];

const TokenSelector = ({ selectedToken, setSelectedToken, className }) => {
  const handleTokenChange = (token) => {
    setSelectedToken(token.label);
  };

  return (
    <div className="flex flex-col gap-2 w-full">
      <span className="text-stormy-gray block text-start w-full">Select Token</span>
      <div className="flex justify-center items-center gap-2 w-full">
        {Tokens.map((token) => (
          <div
            className={`relative w-full text-center rounded-xl border border-border-color h-16 grid place-content-center ${selectedToken === token.label ? "after:content[''] after:absolute after:inset-0 after:p-0.5 after:rounded-xl after:bg-gradient-to-r after:from-nav-button-hover after:to-pink after:[mask:conic-gradient(#000_0_0)_content-box_exclude,conic-gradient(#000_0_0)]" : ''}`}
            key={token.id}
            onClick={() => handleTokenChange(token)}
          >
            <input
              type="radio"
              id={token.id}
              checked={selectedToken === token.label}
              name="token-options"
              value={token.label}
              onChange={() => handleTokenChange(token)}
              className="hidden p-0.5 w-full rounded-xs outline-none"
            />
            <div className="w-full flex gap-1 items-center py-4">
              <div className="bg-border-color rounded-full w-8 h-8 grid place-content-center">
                <span className="rounded-full h-5 w-5 flex justify-center items-center">{token.component}</span>
              </div>
              <label htmlFor={token.id} className="text-base font-semibold text-primary leading-6">
                {token.label}
              </label>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TokenSelector;
