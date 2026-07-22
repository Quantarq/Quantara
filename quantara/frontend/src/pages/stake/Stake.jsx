import React, { useState } from 'react';
import MetricCard from '@/components/vault/metric-card/MetricCard';
import STRK from '@/assets/icons/strk.svg';
import USDCc from '@/assets/icons/apy_icon.svg';
import { VaultLayout } from '@/components/vault/VaultLayout';
import { cn } from '@/utils/cn';
import GasFee from '@/components/vault/gas-fee/GasFee';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({
  amount: z
    .string()
    .regex(/^\d+(\.\d+)?$/, { message: 'Enter a valid amount' })
    .refine((val) => parseFloat(val) > 0, { message: 'Amount must be greater than 0' }),
});

function Stake() {
  const [selectedNetwork, setSelectedNetwork] = useState('Stellar');
  const [showDrop, setShowDrop] = useState(false);

  const networks = [{ name: 'Stellar', image: STRK }];

  const {
    register,
    handleSubmit: rhHandleSubmit,
    formState: { errors, isValid },
  } = useForm({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: { amount: '0' },
  });

  const handleNetworkChange = (network) => {
    setSelectedNetwork(network.name);
  };

  const onSubmit = (data) => {
    // TODO: integrate actual stake logic here
    console.log('Staking amount:', data.amount, 'on network', selectedNetwork);
  };

  return (
    <VaultLayout>
      <div className="flex h-full w-screen flex-col items-center justify-center lg:ml-32 2xl:h-screen">
        <div>
          <h1 className="mt-5 mb-10 text-center text-2xl text-white">Staking</h1>
          <div className="flex h-[103px] w-full items-stretch justify-between space-x-5">
            <MetricCard title="STRK Balance" value="0.046731" icon={STRK} />
            <MetricCard title="APY Balance" value="0.046731" icon={USDCc} />
          </div>
        </div>
        <div className="mt-1.5">
          <p className="mt-3 mb-2 text-center text-lg text-white">Please submit your leverage details</p>
          <div className="mt-5 w-[650px] rounded-lg border border-[#36294e] p-5 px-7 pt-2">
            <div className="w-full">
              <div
                className={cn(
                  'relative border-b border-b-[#36294E] py-1',
                  showDrop ? 'clicked-network-selector-container w-full' : 'network-selector-container'
                )}
                onMouseEnter={() => setShowDrop(true)}
                onMouseLeave={() => setShowDrop(false)}
              >
                <div className="relative z-[10] flex w-full cursor-pointer items-center justify-between gap-3 bg-[#120721] px-4 py-3 text-[1rem] text-white">
                  <div className="flex items-center gap-3">
                    <img
                      src={networks.find((network) => network.name === selectedNetwork)?.image}
                      alt={selectedNetwork}
                      className="network-icon h-6 w-6 rounded-full"
                    />
                    <span className="text-[#83919f]">{selectedNetwork}</span>
                  </div>
                  <svg
                    className={`chevron ml-auto transform transition-transform duration-300 ease-in-out ${showDrop ? 'rotate-[180deg]' : 'rotate-[0deg]'}`}
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                {showDrop && (
                  <div className="network-dropdown shadow-custom absolute top-[100%] left-0 z-[1] w-full rounded-sm group-hover:block">
                    {networks.map((network) => (
                      <div
                        key={network.name}
                        className="network-option my-3 flex cursor-pointer items-center gap-[0.75rem] rounded-[2rem] bg-[#83919f] px-[1rem] py-[0.75rem] text-[#0b0c10] transition-transform duration-300 ease-in-out"
                        onClick={() => handleNetworkChange(network)}
                      >
                        <img src={network.image} alt={network.name} className="network-icon" />
                        <span>{network.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="mt-3 flex w-full items-center justify-center">
              <label className="flex w-full max-w-[140px] min-w-[142px] flex-col justify-center gap-3 font-semibold text-[#393942]">
                <input
                  type="text"
                  id="amount-field"
                  {...register('amount')}
                  className="amount-field w-full border-none bg-transparent text-center text-[64px] font-semibold text-[#83919f] outline-none"
                  placeholder="0.00"
                />
                {errors.amount && <p className="mt-1 text-sm text-red-500">{errors.amount.message}</p>}
                <h3 className="text-center text-sm font-semibold">$0.00 APY / year</h3>
              </label>
              <div className="self-start text-sm font-medium text-[#393942]">STRK</div>
            </div>
            <GasFee />
            <div className="relative mt-5 mb-5 rounded-lg bg-gradient-to-r from-[#74d6fd] to-[#e01dee] p-[1px] transition duration-100 ease-in-out hover:from-[#e01dee] hover:to-[#74d6fd]">
              <button
                className="h-full w-full cursor-pointer rounded-lg bg-[rgb(18,7,33)] px-4 py-4 font-semibold text-white"
                type="button"
                onClick={rhHandleSubmit(onSubmit)}
                disabled={!isValid}
              >
                Stake
              </button>
            </div>
          </div>
        </div>
      </div>
    </VaultLayout>
  );
}

export default Stake;
