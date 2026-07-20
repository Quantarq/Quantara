import React from 'react';
import DiamondIcon from '@/assets/icons/diamond.svg?react';
import TimeIcon from '@/assets/icons/time.svg?react';
import SettingIcon from '@/assets/icons/settings.svg?react';
import MetricCard from '@/components/vault/metric-card/MetricCard';
import { VaultLayout } from '@/components/vault/VaultLayout';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { notify } from '@/components/layout/notifier/Notifier';

const schema = z.object({
  amount: z
    .string()
    .regex(/^\d+(\.\d+)?$/, { message: 'Enter a valid amount' })
    .refine((val) => parseFloat(val) > 0, { message: 'Amount must be greater than 0' }),
});

export default function Withdraw() {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
  } = useForm({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: { amount: '' },
  });

  const onSubmit = (data) => {
    // Placeholder: integrate actual withdraw logic here
    notify(`Withdrawing ${data.amount}`, 'success');
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
                    <DiamondIcon />
                  </span>
                  <span className="text-[#83919f]">Your Stake</span>
                </p>
                <p className="text-2xl font-semibold text-white">13.89</p>
              </div>
              <div className="flex flex-col items-center">
                <p className="flex items-center space-x-2">
                  <span>
                    <TimeIcon />
                  </span>
                  <span className="text-[#83919f]">Your Boost</span>
                </p>
                <p className="text-2xl font-semibold text-white">132.43%</p>
              </div>
            </div>

            <div className="flex flex-col items-start">
              <label htmlFor="withdraw-input" className="mt-10 -mb-3.5 text-[#83919f]">Input Unstake Amount</label>
              <form onSubmit={handleSubmit(onSubmit)}>
                <input
                  type="text"
                  id="withdraw-input"
                  placeholder="Enter Amount to Withdraw"
                  className="mt-4 h-12 w-full rounded-lg border border-[#36294e] px-3 py-7 text-[#83919f] placeholder:text-[#83919f]"
                  {...register('amount')}
                />
                {errors.amount && (
                  <p className="mt-1 text-sm text-red-500">{errors.amount.message}</p>
                )}
                <div className="mt-5">
                  <button
                    type="submit"
                    className="relative mt-5 mb-5 rounded-lg bg-gradient-to-r from-[#74d6fd] to-[#e01dee] p-[2px]"
                    disabled={!isValid}
                  >
                    <div className="h-full w-full cursor-pointer rounded-lg bg-[rgb(18,7,33)] px-4 py-3 font-semibold text-white">
                      Withdraw
                    </div>
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </VaultLayout>
  );
}
