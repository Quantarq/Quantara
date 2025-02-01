import React from 'react';
import DiamondIcon from '@/assets/icons/diamond.svg?react';
import TimeIcon from '@/assets/icons/time.svg?react';
import SettingIcon from '@/assets/icons/settings.svg?react';
import MetricCard from '@/components/vault/metric-card/MetricCard';
import { VaultLayout } from '@/components/vault/VaultLayout';

export default function Withdraw() {
  return (
    <VaultLayout>
      <div className="w-screen h-full 2xl:h-screen flex flex-col justify-center items-center lg:ml-32">
        <div>
          <h1 className="text-2xl text-white text-center mt-5 mb-10">zKLend Withdraw</h1>
          <div className="flex items-center space-x-5">
            <MetricCard title="Total Amount staked" value="324,909,894" />
            <MetricCard title="Daily Boost Multiplier" value="0.5%" />
          </div>
        </div>
        <div className="mt-1.5">
          <p className="text-white text-center text-lg mt-3 -mb-5">Stake Withdrawal</p>
          <div className="border border-[#36294e] p-5 rounded-lg mt-5">
            <div className="flex items-center justify-between bg-[#201338] border border-[#36294e] py-10 px-5 rounded-lg w-[600px]">
              <div className="flex flex-col items-center">
                <p className="flex items-center space-x-2">
                  <span>
                    <DiamondIcon />
                  </span>
                  <span className="text-[#83919f]">Your Stake</span>
                </p>
                <p className="text-white text-2xl font-semibold">13.89</p>
              </div>
              <div className="flex flex-col items-center">
                <p className="flex items-center space-x-2">
                  <span>
                    <TimeIcon />
                  </span>
                  <span className="text-[#83919f]">Your Boost</span>
                </p>
                <p className="text-white text-2xl font-semibold">132.43%</p>
              </div>
            </div>

            <div className="flex flex-col items-start">
              <label htmlFor="withdraw-input" className="text-[#83919f] mt-10 -mb-3.5">
                Input Unstake Amount
              </label>
              <input
                type="text"
                id="withdraw-input"
                placeholder="Enter Amount to Withdraw"
                className="border border-[#36294e] w-full h-12 rounded-lg mt-4 px-3 py-7 placeholder:text-[#83919f] text-[#83919f]"
              />
            </div>

            <div>
              <div className="w-full h-0.5 bg-[#201338] mt-16"></div>
              <div className="mt-3 w-full flex justify-between items-center">
                <div className="bg-[#201338] rounded-full p-2">
                  <SettingIcon />
                </div>
                <p className="text-stormy-gray text-xs">Gas fee: 0.00 STRK</p>
              </div>
            </div>
          </div>
          <div class="relative p-[2px] rounded-lg bg-gradient-to-r from-[#74d6fd] to-[#e01dee] mb-5 mt-5">
            <button class="w-full h-full bg-[rgb(18,7,33)] text-white px-4 py-3 rounded-lg font-semibold cursor-pointer">
              Withdraw
            </button>
          </div>
        </div>
      </div>
    </VaultLayout>
  );
}
