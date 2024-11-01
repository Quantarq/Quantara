import React from 'react';
import { ReactComponent as Star } from '../assets/particles/star.svg';

const StarMaker = ({ starData }) =>
  starData.map((star, index) => (
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
  ));

export default StarMaker;
