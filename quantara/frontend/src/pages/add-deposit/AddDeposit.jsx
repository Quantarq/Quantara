import EthIcon from '@/assets/icons/ethereum.svg?react';
import HealthIcon from '@/assets/icons/health.svg?react';
import Card from '@/components/ui/card/Card';
import { Button } from '@/components/ui/custom-button/Button';
import TokenSelector from '@/components/ui/token-selector/TokenSelector';
import { useAddDeposit } from '@/hooks/useAddDeposit';
import useDashboardData from '@/hooks/useDashboardData';
import { NUMBER_REGEX } from '@/utils/regex';
import { useState } from 'react';
import DashboardLayout from '../DashboardLayout';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({
  amount: z
    .string()
    .regex(/^\d+(\.\d+)?$/, { message: 'Enter a valid amount' })
    .refine((val) => parseFloat(val) > 0, { message: 'Amount must be greater than 0' }),
  selectedToken: z.string().nonempty({ message: 'Select a token' }),
});

export const AddDeposit = () => {
  const { data: dashboardData, isLoading: isDashboardLoading } = useDashboardData();
  const { mutate: addDeposit, isLoading } = useAddDeposit();

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    setValue,
  } = useForm({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: {
      amount: '0',
      selectedToken: 'XLM',
    },
  });

  const onSubmit = (data) => {
    addDeposit(
      {
        positionId: dashboardData?.position_id,
        amount: data.amount,
        tokenSymbol: data.selectedToken,
      },
      {
        onSuccess: () => {
          setValue('amount', '0');
          setValue('selectedToken', 'XLM');
        },
      }
    );
  };

  const selectedToken = watch('selectedToken');

  return (
    <DashboardLayout title="Add Deposit">
      <div className="text-primary flex w-full flex-col items-center justify-center gap-0.5 rounded-lg pt-6 text-center">
        <div className="flex w-full gap-2">
          <Card label="Health Factor" value={dashboardData?.health_ratio} icon={<HealthIcon className="bg-border-color mr-[5px] flex h-8 w-8 items-center justify-center rounded-full p-2" />} labelClassName="text-stormy-gray" />
          <Card label="Borrow Balance" value={formatNumber(dashboardData?.borrowed, true)} icon={<EthIcon className="bg-border-color mr-[5px] flex h-8 w-8 items-center justify-center rounded-full p-2" />} labelClassName="text-stormy-gray" />
        </div>
        <h1 className="text-primary mt-8 mb-0 text-center text-xl font-normal md:mt-0">Please make a deposit</h1>
        <TokenSelector selectedToken={selectedToken} setSelectedToken={(token) => setValue('selectedToken', token)} className="rounded-lg border-none" />
        <div className="relative mx-auto my-8 w-[146px] max-w-[400px] text-center font-semibold">
          <input
            type="text"
            id="amount-field"
            value={watch('amount')}
            onChange={(e) => {
              const value = e.target.value;
              if (NUMBER_REGEX.test(value)) {
                setValue('amount', value);
              }
            }}
            pattern="^\\d*\\.?\\d*$"
            className="text-gray w-full border-none bg-transparent text-center text-[64px] font-semibold outline-none"
            aria-describedby="currency-symbol"
            placeholder="0.00"
            disabled={isLoading || isDashboardLoading}
          />
          <span id="currency-symbol" className="text-dark-gray absolute top-[18%] z-[999999] -translate-x-1/2 -translate-y-1/2 text-base leading-[20.83px] opacity-50">
            {selectedToken}
          </span>
        </div>
        {errors.amount && <p className="mt-1 text-sm text-red-500">{errors.amount.message}</p>}
        {errors.selectedToken && <p className="mt-1 text-sm text-red-500">{errors.selectedToken.message}</p>}
        <Button size="lg" className="mt-4 w-full" variant="primary" onClick={handleSubmit(onSubmit)} disabled={isLoading || isDashboardLoading || !isValid}>
          {isLoading ? 'Processing...' : 'Deposit'}
        </Button>
      </div>
    </DashboardLayout>
  );
};

export default AddDeposit;
