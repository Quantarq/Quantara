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

export const AddDeposit = () => {
  const formatNumber = (value, currency = false) => {
    const number = parseFloat(value);
    if (isNaN(number)) return currency ? '$0.00' : '0';
    return currency ? `$${number.toFixed(2)}` : number.toFixed();
  };

  const [amount, setAmount] = useState('0');
  const [selectedToken, setSelectedToken] = useState('STRK');
  const { data: dashboardData, isLoading: isDashboardLoading } = useDashboardData();

  const { mutate: addDeposit, isLoading } = useAddDeposit();

  const handleAmountChange = (e) => {
    const value = e.target.value;
    if (NUMBER_REGEX.test(value)) {
      setAmount(value);
    }
  };

  const handleDeposit = () => {
    addDeposit(
      {
        positionId: dashboardData?.position_id,
        amount,
        tokenSymbol: selectedToken,
      },
      {
        onSuccess: () => {
          setAmount('0');
          setSelectedToken('STRK');
        },
      }
    );
  };

  return (
    <DashboardLayout title="Add Deposit">
      <div className="flex flex-col w-full items-center justify-center gap-0.5 pt-6 rounded-lg text-primary text-center">
        <div className="flex flex-col md:flex-row w-full gap-2">
          <Card
            label="Health Factor"
            value={dashboardData?.health_ratio}
            icon={<HealthIcon className="mr-[5px] w-4 h-4" />}
            labelClassName="text-stormy-gray"
          />
          <Card
            label="Borrow Balance"
            value={formatNumber(dashboardData?.borrowed, true)}
            icon={<EthIcon className="mr-[5px] w-4 h-4" />}
            labelClassName="text-stormy-gray"
          />
        </div>
      </div>
      <h1 className="text-xl font-normal text-primary text-center mt-8 mb-0 md:mt-0">Please make a deposit</h1>
      <TokenSelector
        selectedToken={selectedToken}
        setSelectedToken={setSelectedToken}
        className="border-none rounded-lg"
      />
      <div className="relative w-[146px] max-w-[400px] mx-auto my-8 text-center font-semibold">
        <input
          type="text"
          id="amount-field"
          value={amount}
          onChange={handleAmountChange}
          pattern="^\d*\.?\d*$"
          className="bg-transparent border-none text-gray text-[64px] font-semibold outline-none text-center w-full"
          aria-describedby="currency-symbol"
          placeholder="0.00"
          disabled={isLoading || isDashboardLoading}
        />
        <span
          id="currency-symbol"
          className="absolute text-dark-gray top-[18%] -translate-x-1/2 -translate-y-1/2 opacity-50 text-base leading-[20.83px] z-[999999]"
        >
          {selectedToken}
        </span>
      </div>

      <Button
        size="lg"
        className="w-full mt-4"
        variant="primary"
        onClick={handleDeposit}
        disabled={isLoading || isDashboardLoading || amount === '0'}
      >
        {isLoading ? 'Processing...' : 'Deposit'}
      </Button>
    </DashboardLayout>
  );
};
