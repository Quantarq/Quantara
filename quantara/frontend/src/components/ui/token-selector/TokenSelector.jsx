import React, { useRef } from 'react';
import ETH from '@/assets/icons/ethereum.svg?react';
import USDC from '@/assets/icons/borrow_usdc.svg?react';
import STRK from '@/assets/icons/strk.svg?react';
import KSTRK from '@/assets/icons/kstrk.svg?react';

const Tokens = [
  { id: 'ethOption', component: <ETH />, label: 'ETH' },
  { id: 'usdcOption', component: <USDC />, label: 'USDC' },
  { id: 'strkOption', component: <STRK />, label: 'STRK' },
  { id: 'KstrkOption', component: <KSTRK />, label: 'KSTRK' },
];

/**
 * TokenSelector — WCAG 2.2 AA compliant radio group.
 *
 * Implements the WAI-ARIA Authoring Practices "Radio Group" pattern
 * (https://www.w3.org/WAI/ARIA/apg/patterns/radio/):
 *   • `role="radiogroup"` wrapper with optional `aria-labelledby`
 *   • `role="radio"` items with `aria-checked`
 *   • Roving `tabIndex` so only the focused/checked radio is in tab order
 *   • Arrow keys (Left/Right/Up/Down) move focus between radios
 *   • Home/End jump to the first/last radio
 *   • Space/Enter select the focused radio
 *
 * Visual styling is unchanged; only aria semantics + keyboard semantics
 * were added for issue #272.
 */
const TokenSelector = ({ selectedToken, setSelectedToken, className, ariaLabelledBy }) => {
  const groupRef = useRef(null);

  const focusTokenAt = (idx) => {
    const items = groupRef.current?.querySelectorAll('[role="radio"]');
    if (!items || !items[idx]) return;
    items[idx].focus();
  };

  const onGroupKeyDown = (e) => {
    const currentIdx = Tokens.findIndex((t) => t.label === selectedToken);
    let nextIdx = currentIdx;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextIdx = (currentIdx + 1) % Tokens.length;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp')
      nextIdx = (currentIdx - 1 + Tokens.length) % Tokens.length;
    else if (e.key === 'Home') nextIdx = 0;
    else if (e.key === 'End') nextIdx = Tokens.length - 1;
    else return;
    e.preventDefault();
    setSelectedToken(Tokens[nextIdx].label);
    focusTokenAt(nextIdx);
  };

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={ariaLabelledBy ? undefined : 'Select Token'}
      aria-labelledby={ariaLabelledBy}
      onKeyDown={onGroupKeyDown}
      className={`flex flex-col w-full gap-2 ${className ?? ''}`}
    >
      <span className="block w-full text-stormy-gray text-start">Select Token</span>
      <div className="flex items-center justify-center w-full gap-2">
        {Tokens.map((token) => {
          const checked = selectedToken === token.label;
          return (
            <div
              key={token.id}
              role="radio"
              tabIndex={checked ? 0 : -1}
              aria-checked={checked}
              aria-label={token.label}
              onClick={(e) => {
                setSelectedToken(token.label);
                // Move focus to the clicked radio so subsequent arrow-key
                // navigation starts from the newly-selected item.
                e.currentTarget.focus();
              }}
              onKeyDown={(e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                  e.preventDefault();
                  setSelectedToken(token.label);
                }
              }}
              className={`border-border-color relative grid h-16 w-full place-content-center rounded-xl border text-center cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
                checked
                  ? "after:content-[''] after:from-nav-button-hover after:to-pink after:absolute after:inset-0 after:rounded-xl after:bg-gradient-to-r after:p-0.5 after:[mask:conic-gradient(#000_0_0)_content-box_exclude,conic-gradient(#000_0_0)]"
                  : ''
              }`}
            >
              <input
                type="radio"
                id={token.id}
                checked={checked}
                name="token-options"
                value={token.label}
                onChange={() => setSelectedToken(token.label)}
                tabIndex={-1}
                className="sr-only"
              />
              <div className="flex items-center w-full gap-1 py-4">
                <div className="grid w-8 h-8 rounded-full bg-border-color place-content-center">
                  <span className="flex items-center justify-center w-5 h-5 rounded-full">
                    {token.component}
                  </span>
                </div>
                <label
                  htmlFor={token.id}
                  className="text-base font-semibold leading-6 text-primary"
                  onClick={(e) => e.preventDefault()}
                >
                  {token.label}
                </label>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Small inline helper so it doesn't leak to the rest of the bundle.
function handleSelect(token, setSelectedToken) {
  setSelectedToken(token.label);
}

export default TokenSelector;
