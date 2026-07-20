import React, { useState, useId } from 'react';
import DiamondIcon from '@/assets/icons/diamond.svg?react';
import TimeIcon from '@/assets/icons/time.svg?react';
import SettingIcon from '@/assets/icons/settings.svg?react';
import MetricCard from '@/components/vault/metric-card/MetricCard';
import { VaultLayout } from '@/components/vault/VaultLayout';
import { Button } from '@/components/ui/custom-button/Button';

const ErrorIcon = () => (
  <span
    aria-hidden="true"
    className="inline-block h-4 w-4 rounded-full bg-error text-[10px] font-bold leading-4 text-white"
  >
    !
  </span>
);

export default function Withdraw() {
  const [amount, setAmount] = useState('');
  const [amountError, setAmountError] = useState('');
  const inputId = useId();
  const errorId = useId();

  const handleWithdraw = (e) => {
    e.preventDefault();
    if (!amount || isNaN(Number(amount)) || Number(amount) <= 0) {
      setAmountError('Please enter a valid amount to unstake.');
      return;
    }
    setAmountError('');
    // TODO: wire to actual withdraw handler
  };

  return (
    <VaultLayout>
      <div className="flex h-full w-screen flex-col items-center justify-center lg:ml-32 2xl:h-screen">
        <div>
          <h1 className="mt-5 mb-10 text-center text-2xl text-white">Withdraw</h1>
          <div className="flex items-center space-x-5">
            <MetricCard title="Total Amount staked" value="324,909,894" />
            <MetricCard title="Daily Boost Multiplier" value="0.5%" />
          </div>
        </div>
        <div className="mt-1.5">
          <p className="mt-3 -mb-5 text-center text-lg text-white">Stake Withdrawal</p>
          <div className="mt-5 rounded-lg border border-[#36294e] p-5">
            <div className="flex w-[600px] items-center justify-between rounded-lg border border-[#36294e] bg-[#201338] px-5 py-10">
              <div className="flex flex-col items-center">
                <p className="flex items-center space-x-2">
                  <span>
                    <DiamondIcon aria-hidden="true" />
                  </span>
                  <span className="text-[#83919f]">Your Stake</span>
                </p>
                <p className="text-2xl font-semibold text-white">13.89</p>
              </div>
              <div className="flex flex-col items-center">
                <p className="flex items-center space-x-2">
                  <span>
                    <TimeIcon aria-hidden="true" />
                  </span>
                  <span className="text-[#83919f]">Your Boost</span>
                </p>
                <p className="text-2xl font-semibold text-white">132.43%</p>
              </div>
            </div>

            <form className="flex flex-col items-start" onSubmit={handleWithdraw} noValidate>
              <label htmlFor={inputId} className="mt-10 -mb-3.5 text-[#83919f]">
                Input Unstake Amount
              </label>
              <div className="relative mt-4 w-full">
                <input
                  type="number"
                  id={inputId}
                  placeholder="Enter Amount to Withdraw"
                  value={amount}
                  onChange={(e) => {
                    setAmount(e.target.value);
                    if (amountError) setAmountError('');
                  }}
                  aria-invalid={amountError ? 'true' : 'false'}
                  aria-describedby={amountError ? errorId : undefined}
                  className={`h-12 w-full rounded-lg border border-[#36294e] bg-[#201338] px-3 py-7 pr-10 text-[#83919f] placeholder:text-[#83919f] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
                    amountError ? 'border-error' : ''
                  }`}
                />
                {amountError && (
                  <span
                    aria-hidden="true"
                    className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2"
                  >
                    <ErrorIcon />
                  </span>
                )}
              </div>
              {amountError && (
                <p
                  id={errorId}
                  role="alert"
                  className="text-error mt-2 flex items-center gap-1.5 text-sm"
                >
                  <ErrorIcon />
                  <span>{amountError}</span>
                </p>
              )}

              <div className="w-full">
                <div className="mt-16 h-0.5 w-full bg-[#201338]"></div>
                <div className="mt-3 flex w-full items-center justify-between">
                  <div className="rounded-full bg-[#201338] p-2">
                    <SettingIcon aria-hidden="true" />
                  </div>
                  <p className="text-stormy-gray text-xs">Gas fee: 0.00 STRK</p>
                </div>
              </div>
              <div className="relative mt-5 mb-5 w-full rounded-lg bg-gradient-to-r from-[#74d6fd] to-[#e01dee] p-[2px]">
                <Button type="submit" variant="primary" size="lg" className="h-full w-full">
                  Withdraw
                </Button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </VaultLayout>
  );
}
