import React, { useState } from 'react';
import TokenSelector from '@/components/ui/token-selector/TokenSelector';
import BalanceCards from '@/components/ui/balance-cards/BalanceCards';
import MultiplierSelector from '@/components/ui/multiplier-selector/MultiplierSelector';
import { handleTransaction } from '@/services/transaction';
import Spinner from '@/components/ui/spinner/Spinner';
import { Button } from '@/components/ui/custom-button/Button';
import { useWalletStore } from '@/stores/useWalletStore';
import { useConnectWallet } from '@/hooks/useConnectWallet';
import { useCheckPosition } from '@/hooks/useClosePosition';
import { useNavigate } from 'react-router-dom';
import { ActionModal } from '@/components/ui/action-modal';
import { useHealthFactor } from '@/hooks/useHealthRatio';
import { notify } from '@/components/layout/notifier/Notifier';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({
  tokenAmount: z
    .string()
    .regex(/^\d+(\.\d+)?$/, { message: 'Enter a valid amount' })
    .refine((val) => parseFloat(val) > 0, { message: 'Amount must be greater than 0' }),
  selectedToken: z.string().nonempty({ message: 'Select a token' }),
  selectedMultiplier: z.string().nonempty({ message: 'Select a multiplier' }),
});

const Form = () => {
  const navigate = useNavigate();
  const { walletId, setWalletId } = useWalletStore();
  const [loading, setLoading] = useState(false);
  const [isClosePositionOpen, setClosePositionOpen] = useState(false);
  const connectWalletMutation = useConnectWallet(setWalletId);
  const { data: positionData, refetch: refetchPosition } = useCheckPosition();
  const { healthFactor, isLoading: isHealthFactorLoading } = useHealthFactor(
    // placeholder; will be updated via watch if needed
    '',
    '',
    ''
  );

  const {
    control,
    register,
    handleSubmit: rhHandleSubmit,
    formState: { errors, isValid },
    watch,
    setValue,
  } = useForm({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: {
      tokenAmount: '',
      selectedToken: 'ETH',
      selectedMultiplier: '',
    },
  });

  const selectedToken = watch('selectedToken');
  const selectedMultiplier = watch('selectedMultiplier');

  const connectWalletHandler = () => {
    if (!walletId) {
      connectWalletMutation.mutate();
    }
  };

  const onSubmit = async (data) => {
    let connectedWalletId = walletId;
    if (!connectedWalletId) {
      connectWalletHandler();
      return;
    }
    await refetchPosition();
    if (positionData?.has_opened_position) {
      setClosePositionOpen(true);
      return;
    }
    const formData = {
      wallet_id: connectedWalletId,
      token_symbol: data.selectedToken,
      amount: data.tokenAmount,
      multiplier: data.selectedMultiplier,
    };
    await handleTransaction(connectedWalletId, formData, () => setValue('tokenAmount', ''), setLoading);
  };

  const onClosePositionAction = () => {
    navigate('/dashboard');
  };

  return (
    <div className="flex min-h-screen flex-col items-center gap-4 py-4">
      <BalanceCards />

      {isClosePositionOpen && (
        <ActionModal
          isOpen={isClosePositionOpen}
          title="Open New Position"
          subTitle="Do you want to open new a position?"
          content={[
            'You have already opened a position.',
            'Please close active position to open a new one.',
            "Click the 'Close Active Position' button to continue.",
          ]}
          cancelLabel="Cancel"
          submitLabel="Close Active Position"
          submitAction={onClosePositionAction}
          cancelAction={() => setClosePositionOpen(false)}
        />
      )}

      <form className="text-primary flex w-full max-w-2xl flex-col justify-center gap-2.5 px-4 pb-3 sm:px-2" onSubmit={rhHandleSubmit(onSubmit)}>
        <div className="mt-0 mb-3 text-sm font-normal sm:my-3.5 md:mb-2.5">
          <h2 className="text-center text-lg sm:text-xl">Please submit your leverage details</h2>
        </div>
        <Controller
          name="selectedToken"
          control={control}
          render={({ field }) => (
            <TokenSelector {...field} className="form-token-selector" />
          )}
        />
        {errors.selectedToken && <p className="mt-1 text-sm text-red-500">{errors.selectedToken.message}</p>}
        <div className="text-gray text-4 w-full pt-2">
          <label>Select Multiplier</label>
        </div>
        <Controller
          name="selectedMultiplier"
          control={control}
          render={({ field }) => (
            <MultiplierSelector {...field} sliderValue={field.value} />
          )}
        />
        {errors.selectedMultiplier && <p className="mt-1 text-sm text-red-500">{errors.selectedMultiplier.message}</p>}
        <div className="mt-16 mb-2 flex w-full flex-col gap-1.5">
          <label className="text-gray w-full pt-5 pb-2 text-start">Token Amount</label>
          <input
            className="border-light-purple w-full [appearance:textfield] rounded-xl border bg-transparent px-6 py-5 text-sm focus:outline-0 sm:px-8 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            type="text"
            placeholder="Enter Token Amount"
            {...register('tokenAmount')}
          />
          {errors.tokenAmount && <p className="mt-1 text-sm text-red-500">{errors.tokenAmount.message}</p>}
        </div>
        <div className="w-full">
          <div className="text-gray mb-7 flex w-fit flex-row items-end gap-1.5 self-end justify-self-end sm:mb-8">
            <p>Estimated Health Factor Level:</p>
            <p>{isHealthFactorLoading ? 'Loading...' : healthFactor}</p>
          </div>
          <Button variant="secondary" size="lg" type="submit" className="form-button" disabled={!isValid || loading}>
            Submit
          </Button>
        </div>
      </form>
      <Spinner loading={loading} />
    </div>
  );
};

export default Form;
