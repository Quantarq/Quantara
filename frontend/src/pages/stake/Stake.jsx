import React, { useState } from 'react';
import MetricCard from '@/components/vault/stake-card/StakeCard';
import STRK from '@/assets/icons/strk.svg';
import USDCc from '@/assets/icons/apy_icon.svg';
import { VaultLayout } from '@/components/vault/VaultLayout';
import { Button } from '@/components/ui/custom-button/Button';
import GasFee from '@/components/vault/gas-fee/GasFee';
import BalanceCards from '@/components/ui/balance-cards/BalanceCards';
import { cn } from '@/utils/cn';

function Stake() {
  const [selectedNetwork, setSelectedNetwork] = useState('Starknet');
  const [amount, setAmount] = useState('0');
  const [showDrop, setShowDrop] = useState(false);

  const networks = [
    { name: 'Starknet', image: STRK },
    { name: 'alephium', image: STRK },
  ];
  const handleChange = (network) => {
    setSelectedNetwork(network.name);
  };

  const handleAmountChange = (e) => {
    const value = e.target.value;
    const regex = /^\d*\.?\d*$/;
    if (regex.test(value)) {
      setAmount(value);
    }
  };
  return (
    <VaultLayout>
      <div className="stake-wrapper font-primary bg-cover bg-39p min-h-[125vh] h-full flex justify-center w-[calc(100vw-372px)] ml-[372px] mt-[70px] mb-[100px]">
        <div className="stake-container w-full max-w-[642px] h-[610px] my-0 mx-auto flex flex-col items-center  gap-4 ">
          <h1 className=" font-semibold text-2xl text-(--primary) mt-10 mb-5">zkLend Staking</h1>
          <div className="w-full flex flex-row justify-between items-center gap-6">
            <MetricCard title="STRK Balance" value="0.046731" icon={STRK} />
            <MetricCard title="APY Balance" value="0.046731" icon={USDCc} />
          </div>
          <p className=" text-[#F0F0F0] font-normal text-sm">Please submit your leverage details</p>

          <div className="border border-[#36294E] w-full max-h-[503px]  rounded-lg py-3 flex  flex-col ">
            <div className="w-full px-4">
              <div
                className={cn(
                  'py-3 border-b border-b-[#36294E] relative',
                  showDrop ? 'clicked-network-selector-container  w-full' : 'network-selector-container'
                )}
                onMouseEnter={() => setShowDrop(true)}
                onMouseLeave={() => setShowDrop(false)}
              >
                <div className="network-selector flex items-center justify-between gap-3 bg-[#120721]  text-white py-3 px-4 cursor-pointer text-[1rem] w-full relative z-[10] ">
                  <div className="selected-network flex items-center gap-3">
                    <img
                      src={networks.find((network) => network.name === selectedNetwork)?.image}
                      alt={selectedNetwork}
                      className="network-icon w-6 h-6 rounded-full  "
                    />
                    <span>{selectedNetwork}</span>
                  </div>
                  <svg
                    className="chevron transition-transform duration-300 ease-in-out ml-auto  group-hover:rotate(180deg) transform "
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M6 9L12 15L18 9"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>

                {showDrop && (
                  <div className="network-dropdown absolute top-[100%] left-0 w-full rounded-sm z-[1] shadow-custom group-hover:block">
                    {networks.map((network) => (
                      <div
                        key={network.name}
                        className={`network-option py-[0.75rem] px-[1rem] my-3 bg-[#36294E] text-white flex  items-center gap-[0.75rem] cursor-pointer rounded-[2rem] transition-transform duration-300 ease-in-out ${showDrop ? 'visibile' : 'invisible'} `}
                        onClick={() => handleChange(network)}
                      >
                        <img src={network.image} alt={network.name} className="network-icon" />
                        <span>{network.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div
              className="w h-[158px] flex flex-row justify-center items-center my-15"
              aria-labelledby="amount-input-label"
            >
              <label className="w-full text-[#393942] min-w-[182px] max-w-[200px]  font-semibold flex flex-col  justify-center gap-3 ">
                <input
                  type="text"
                  id="amount-field"
                  value={amount}
                  onChange={handleAmountChange}
                  pattern="^\d*\.?\d*$"
                  className="amount-field  bg-transparent border-none text-[#83919f] text-[64px] font-semibold outline-none text-center w-full "
                  aria-describedby="currency-symbol"
                  placeholder="0.00"
                  style={{
                    fontSize: '64px',
                  }}
                />
                <h3 className="font-semibold text-sm text-center">$0.00 APY / year</h3>
              </label>
              <div className="self-start text-[#393942] font-medium text-sm  ">STRK</div>
            </div>

            <div className="w-full px-4 ">
              {' '}
              <GasFee />
            </div>
          </div>
          <div className="p-[4px] rounded-lg">
            <Button variant="secondary" size="lg">
              Stake
            </Button>
          </div>
        </div>
      </div>
    </VaultLayout>
  );
}

export default Stake;
