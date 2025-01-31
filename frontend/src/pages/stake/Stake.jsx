import React, { useState } from 'react';
import MetricCard from '@/components/vault/metric-card/MetricCard';
import STRK from '@/assets/icons/strk.svg';
import USDCc from '@/assets/icons/apy_icon.svg';
import { VaultLayout } from '@/components/vault/VaultLayout';
import { cn } from '@/utils/cn';
import GasFee from '@/components/vault/gas-fee/GasFee';

function Stake() {
  const [selectedNetwork, setSelectedNetwork] = useState('Starknet');
  const [amount, setAmount] = useState('0');
  const [showDrop, setShowDrop] = useState(false);

  const networks = [
    { name: 'Starknet', image: STRK },
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
      <div className="w-screen h-full  min-h-screen p-[7%]  2xl:h-screen flex flex-col justify-center items-center lg:ml-32">
        <div className='w-full max-w-[650px] h-full flex flex-col items-center justify-center' >
          <h1 className="text-2xl text-white text-center mt-5 mb-10">zkLend Staking</h1>
          <div className="w-full flex items-stretch h-[103px] justify-between space-x-5    ">
            <MetricCard title="STRK Balance" value="0.046731" icon={STRK} />
            <MetricCard title="APY Balance" value="0.046731" icon={USDCc} />
          </div>

          <div className="mt-1.5">
            <p className="text-white text-center text-lg mt-3 mb-2">Please submit your leverage details</p>
            <div className="border border-[#36294e] p-5 pt-2 px-7 rounded-lg mt-5 w-[650px]">


              <div className="w-full">
                <div
                  className={cn(
                    'py-1 border-b border-b-[#36294E] relative',
                    showDrop ? 'clicked-network-selector-container  w-full' : 'network-selector-container'
                  )}
                  onMouseEnter={() => setShowDrop(true)}
                  onMouseLeave={() => setShowDrop(false)}
                >
                  <div className=" flex items-center justify-between gap-3 bg-[#120721]  text-white py-3 px-4 cursor-pointer text-[1rem] w-full relative z-[10] ">
                    <div className=" flex items-center gap-3">
                      <img
                        src={networks.find((network) => network.name === selectedNetwork)?.image}
                        alt={selectedNetwork}
                        className="network-icon w-6 h-6 rounded-full  "
                      />
                      <span>{selectedNetwork}</span>
                    </div>
                    <svg
                      className={`chevron transition-transform duration-300 ease-in-out ml-auto   transform ${showDrop ? "rotate-[180deg] " : "rotate-[0deg]"} `}
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
                          className={`network-option py-[0.75rem] px-[1rem] my-3 bg-[#83919f] text-[#0b0c10] flex  items-center gap-[0.75rem] cursor-pointer rounded-[2rem] transition-transform duration-300 ease-in-out ${showDrop ? 'visibile' : 'invisible'} `}
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
                <label className="w-full text-[#393942] min-w-[142px] max-w-[140px]  font-semibold flex flex-col  justify-center gap-3 ">
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


              <GasFee />
            </div>
            <div class="relative p-[1px] rounded-lg bg-gradient-to-r from-[#74d6fd] to-[#e01dee] mb-5 mt-5 
hover:from-[#e01dee] hover:to-[#74d6fd] transition duration-100 ease-in-out ">
              <button class="w-full h-full bg-[rgb(18,7,33)] text-white px-4 py-4 rounded-lg font-semibold cursor-pointer">
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
