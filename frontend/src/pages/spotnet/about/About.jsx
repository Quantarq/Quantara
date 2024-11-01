import './about.css';
import { ReactComponent as Star } from 'assets/particles/star.svg';
import { ReactComponent as ZkLend } from 'assets/icons/zklend_eth_collateral.svg';
import { ReactComponent as BorrowUSDC } from 'assets/icons/borrow_usdc.svg';
import { ReactComponent as EkuboSwap } from 'assets/icons/ekubo_swap.svg';
import { ReactComponent as Repeat } from 'assets/icons/repeats.svg';
import React from 'react';

const CardData = [
  {
    number: '1',
    title: 'ZkLend ETH collateral',
    description:
      'ETH/STRK from your wallet is deposited as collateral on ZkLend.',
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
    <div className='about-container'>
      {starData.map((star, index) => (
        <Star
          key={index}
          style={{
            position: 'absolute',
            top: `${star.top}%`,
            left: `${star.left}%`,
            width: `${star.size}%`,
            height: `${star.size}%`,
          }}
        />
      ))}
      <h1 className='about-title'>How it works</h1>
      <div className='card-container flex'>
        <div className='card-gradients'>
          <div className='card-gradient'></div>
          <div className='card-gradient'></div>
        </div>
        {CardData.map((card, index) => (
          <div key={index} className='card-about flex'>
            <div className='card-number flex'>
              <h2>{card.number}</h2>
            </div>
            <div className='card-icon'>
              <card.icon />
            </div>
            <div className='card-title'>
              <h4>{card.title}</h4>
            </div>
            <div className='card-description'>
              <h6>{card.description}</h6>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default About;
