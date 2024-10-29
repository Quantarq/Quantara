import React from 'react';

const Multipliers = [
  { id: 'option1', value: 'x5', recommended: true },
  { id: 'option2', value: 'x4', recommended: false },
  { id: 'option3', value: 'x3', recommended: false },
  { id: 'option4', value: 'x2', recommended: false },
];

const MultiplierSelector = ({ setSelectedMultiplier }) => (
  <div className='multiplier-card'>
    {Multipliers.map((multiplier) => (
      <div className={'multiplier-item'} key={multiplier.id}>
        {multiplier.recommended && (
          <div className='recommended'>
            <p>Recommended</p>
          </div>
        )}
        <input
          type='radio'
          id={multiplier.id}
          name='card-options'
          value={multiplier.value}
          onChange={() =>
            setSelectedMultiplier(multiplier.value.replace('x', ''))
          }
        />
        <label
          htmlFor={multiplier.id}
          className={multiplier.recommended ? 'recommended-item' : ''}
        >
          {multiplier.value}
        </label>
      </div>
    ))}
  </div>
);

export default MultiplierSelector;
