import React, { useMemo, useCallback, useState } from 'react';
import { useMaxMultiplier } from 'hooks/useMaxMultiplier';
import './multiplier.css';

const MultiplierSelector = ({ setSelectedMultiplier, selectedToken }) => {
  const { data, isLoading, error } = useMaxMultiplier();
  const [actualValue, setActualValue] = useState(1.0);

  const maxMultiplier = useMemo(() => {
    return data?.[selectedToken] || 11.0;
  }, [data, selectedToken]);

  const TOTAL_MARKS = 11;
  const STEP_SIZE = maxMultiplier / (TOTAL_MARKS - 1);

  const mapSliderToValue = useCallback((sliderValue) => {
    const stepValue = Math.round((maxMultiplier - sliderValue + 1) / STEP_SIZE) * STEP_SIZE;
    return Math.min(maxMultiplier, Math.max(1, stepValue));
  }, [maxMultiplier]);

  const handleMultiplierChange = useCallback(
    (e) => {
      const sliderValue = parseFloat(e.target.value);
      const value = mapSliderToValue(sliderValue).toFixed(1);
      setActualValue(value);
      setSelectedMultiplier(value);
    },
    [setSelectedMultiplier, mapSliderToValue]
  );

  const getSliderPercentage = useCallback(() => {
    return ((maxMultiplier - actualValue + 1 - 1) / (maxMultiplier - 1)) * 100;
  }, [actualValue, maxMultiplier]);

  const getCurrentMark = useCallback(() => {
    const invertedValue = maxMultiplier - actualValue + 1;
    const markIndex = Math.round((invertedValue - 1) * (TOTAL_MARKS - 1) / (maxMultiplier - 1));
    return Math.min(Math.max(0, markIndex), TOTAL_MARKS - 1);
  }, [actualValue, maxMultiplier, TOTAL_MARKS]);

  if (isLoading) return <div className="slider-skeleton">Loading multiplier data...</div>;
  if (error) return <div className="error-message">Error loading multiplier data: {error.message}</div>;

  const style = {
    background: `linear-gradient(to right, 
      var(--brand),
      var(--pink) ${getSliderPercentage()}%, 
      rgba(0, 0, 0, 0.1) ${getSliderPercentage()}%)`
  };
  const currentMark = getCurrentMark();

  return (
    <div className="multiplier-card">
      <div className="slider-container">
        <div className="slider-labels">
          <span>Max</span>
          <span>Low</span>
        </div>
        <div className="slider-with-tooltip">
          <div className="multiplier-slider-outer">
            <div className="multiplier-slider-inner">
              <input
                type="range"
                min="1"
                max={maxMultiplier}
                step={STEP_SIZE}
                value={maxMultiplier - actualValue + 1}
                onChange={handleMultiplierChange}
                style={style}
                className="multiplier-slider"
              />
            </div>
          </div>
        </div>
        <div className="range-meter">
          {Array.from({ length: TOTAL_MARKS }).map((_, index) => (
            <div
              key={index}
              className={`meter-inner ${index === currentMark ? 'active' : ''}`}
            >
              <div className={`meter-marks ${index === currentMark ? 'active' : ''}`}></div>
              <div className={`meter-label ${index === currentMark ? 'active' : ''}`}>
                {index}x
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MultiplierSelector;