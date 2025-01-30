import React from 'react';
// import './withdraw.css';
import DiamondIcon from '@/assets/icons/diamond.svg?react';
import TimeIcon from '@/assets/icons/time.svg?react';
import SettingIcon from '@/assets/icons/settings.svg?react';
import MetricCard from '@/components/vault/metric-card/MetricCard';
import { VaultLayout } from '@/components/vault/VaultLayout';

export default function Withdraw() {
  return (
    <VaultLayout>
      <div className="w-screen h-screen flex flex-col justify-center items-center">
        <div>
          <h1 className="!text-lg text-white text-center">zKLend Withdraw</h1>
          <div className="flex items-center space-x-5">
            <MetricCard title="Total Amount staked" value="324,909,894" />
            <MetricCard title="Daily Boost Multiplier" value="0.5%" />
          </div>
        </div>
        <div>
          <p className="text-(--primary)">Staking Withdrawal</p>
          <div>
            <div>
              <div>
                <p>
                  <span>
                    <DiamondIcon />
                  </span>
                  <span>Your Stake</span>
                </p>
                <p>13.89</p>
              </div>
              <div>
                <p>
                  <span>
                    <TimeIcon />
                  </span>
                  <span>Your Boost</span>
                </p>
                <p>132.43%</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </VaultLayout>
  );
}
