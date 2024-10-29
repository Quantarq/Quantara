import './information.css';
import { ReactComponent as Star } from 'assets/particles/star.svg';
import React from 'react';

const Informaion = () => {
  const starData = [
    { top: 9, left: -6.2, size: 20 },
    { top: 9, left: 39, size: 15 },
    { top: -8, left: 85, size: 18 },
    { top: 74, left: 43, size: 22 },
  ];
  return (
    <div className='information'>
      <div className='card-info__container'>
        <div className='card-info flex'>
          <h1>TVL</h1>
          <h3>$245.7k</h3>
        </div>
        <div className='card-gradients infos'>
          <div className='card-gradient'></div>
          <div className='card-gradient'></div>
        </div>
        <div className='card-info flex'>
          <h1>TVL</h1>
          <h3>$245.7k</h3>
        </div>
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
      </div>
    </div>
  );
};

export default Informaion;
