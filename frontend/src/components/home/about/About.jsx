import React from 'react';
import ZkLend from '@/assets/icons/zklend_eth_collateral.svg?react';
import BorrowUSDC from '@/assets/icons/borrow_usdc.svg?react';
import EkuboSwap from '@/assets/icons/ekubo_swap.svg?react';
import Repeat from '@/assets/icons/repeats.svg?react';
import StarMaker from '@/components/layout/star-maker/StarMaker';


const CardData = [
  {
    number: '1',
    title: 'ZkLend ETH collateral',
    description: 'ETH/STRK from your wallet is deposited as collateral on ZkLend.',
    icon: ZkLend,
  },
  {
    number: '2',
    title: 'Borrow USDC',
    description: 'You borrow USDC against that collateral.',
    icon: BorrowUSDC,
  },
  {
    number: '3',
    title: 'Ekubo Swap',
    description: 'The USDC is swapped back to ETH on Ekubo.',
    icon: EkuboSwap,
  },
  {
    number: '4',
    title: 'Repeats',
    description: 'The process repeats, compounding up to five times.',
    icon: Repeat,
  },
];

const About = () => {
  const starData = [
    { top: 10, left: 5, size: 5 },
    { top: 85, left: 10, size: 10 },
    { top: 7, left: 80, size: 8 },
  ];

  return (
    <div className=" relative flex flex-col  items-center justify-between w-[100%] bg-black lg:mb-[350px] mb-[100px] p-0">
      <StarMaker starData={starData} />
      <h1 className=" text-center font-text text-white mt-[64px] text-[48px] font-[600] mb-[180px] ">How it works</h1>
      
      <div className="flex flex-wrap gap-[5em] sm:gap-[4em] lg:gap-[2em] justify-center  px-4 max-w-7xl mx-auto">
        {CardData.map((card, index) => ( 
          <div key={index} className="relative flex flex-col items-center">
            <div className="absolute -top-[2em] md:-top-[1em] lg:-top-[1.5em] 2xl:-top-[1.5em] z-10 left-1/2 -translate-x-1/2">
              <div className="bg-primary-color border border-[#74d6fd] border-[0.8px] text-brand font-text font-semibold 
                text-[32px] px-4 py-1 rounded-xl min-w-[70px] text-center
                xl:text-[30px] bg-black lg:text-[25px] lg:min-w-[60px] md:text-[18px] md:min-w-[45px] text-[#74d6fd]">
                {card.number}
              </div>
            </div>
            
            <div className="w-[310px] h-[368px]  flex flex-col items-center gap-4 px-4 pt-[3em] 2xl:pt-[3em] bg-[linear-gradient(135deg,_rgba(116,_214,_253,_0.5)_0%,_rgba(11,_12,_16,_0.5)_100%)] 
              rounded-[20px] border border-[#4e7787] shadow-card backdrop-blur-[21.09375px]
              xl:w-[260px] xl:h-[300px] lg:w-[220px] lg:h-[255px] md:w-[175px] md:h-[205px]">
              
              <div className="flex justify-center items-center w-[120px] h-[120px]
                xl:w-[100px] xl:h-[100px] lg:w-[80px] lg:h-[80px] md:w-[60px] md:h-[60px]">
                <card.icon />
              </div>
              
              <h4 className="font-text text-[26px] text-primary text-center leading-[108%] font-medium
                xl:text-[20px] text-white lg:text-[18px] md:text-[15px]">
                {card.title}
              </h4>
              
              <p className="font-text text-[20px] text-white text-secondary text-center leading-[140%] font-normal
                xl:text-base lg:text-sm md:text-[11px]">
                {card.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default About;