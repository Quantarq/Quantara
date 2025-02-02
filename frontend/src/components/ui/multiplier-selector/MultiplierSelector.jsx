import React, { useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { useMaxMultiplier } from '@/hooks/useMaxMultiplier';
import sliderThumb from '@/assets/icons/slider_thumb.svg';

const MultiplierSelector = ({ setSelectedMultiplier, selectedToken }) => {
  const minMultiplier = 1.1;

  const { data, isLoading } = useMaxMultiplier();
  const [actualValue, setActualValue] = useState(minMultiplier);
  const sliderRef = useRef(null);
  const isDragging = useRef(false);

  const maxMultiplier = useMemo(() => {
    return data?.[selectedToken] || 5.0;
  }, [data, selectedToken]);

  const marks = useMemo(() => {
    const marksArray = [];
    for (let i = Math.ceil(minMultiplier); i <= Math.floor(maxMultiplier); i++) {
      marksArray.push(i);
    }
    marksArray.unshift(minMultiplier);
    if (!marksArray.includes(maxMultiplier)) {
      marksArray.push(maxMultiplier);
    }
    return marksArray;
  }, [minMultiplier, maxMultiplier]);

  const mapSliderToValue = useCallback(
    (sliderPosition) => {
      const rect = sliderRef.current.getBoundingClientRect();
      const percentage = sliderPosition / rect.width;
      const value = percentage * (maxMultiplier - minMultiplier) + minMultiplier;
      return Math.max(minMultiplier, Math.min(maxMultiplier, parseFloat(value.toFixed(1))));
    },
    [maxMultiplier, minMultiplier]
  );

  const calculateSliderPercentage = useCallback(
    (value) => {
      const percentage = ((value - minMultiplier) / (maxMultiplier - minMultiplier)) * 100;
      return Math.min(Math.max(percentage, 0), 100);
    },
    [maxMultiplier, minMultiplier]
  );

  const updateSliderValue = useCallback(
    (clientX) => {
      const slider = sliderRef.current;
      if (!slider) return;

      const rect = slider.getBoundingClientRect();
      const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
      const newValue = mapSliderToValue(x);

      setActualValue(newValue);
      setSelectedMultiplier(newValue.toFixed(1));
    },
    [mapSliderToValue, setSelectedMultiplier]
  );

  const handleDrag = (e) => {
    if (!isDragging.current) return;
    const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
    updateSliderValue(clientX);
  };

  const handleMouseDown = (e) => {
    isDragging.current = true;
    updateSliderValue(e.clientX);
  };

  const handleTouchStart = (e) => {
    isDragging.current = true;
    updateSliderValue(e.touches[0].clientX);
  };

  const handleDragEnd = () => {
    isDragging.current = false;
  };

  useEffect(() => {
    document.addEventListener('mousemove', handleDrag);
    document.addEventListener('mouseup', handleDragEnd);
    document.addEventListener('touchmove', handleDrag);
    document.addEventListener('touchend', handleDragEnd);

    return () => {
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', handleDragEnd);
      document.removeEventListener('touchmove', handleDrag);
      document.removeEventListener('touchend', handleDragEnd);
    };
  }, [handleDrag]);

  useEffect(() => {
    if (actualValue > maxMultiplier) {
      setActualValue(maxMultiplier);
      setSelectedMultiplier(maxMultiplier.toFixed(1));
    } else {
      setSelectedMultiplier(actualValue.toFixed(1));
    }
  }, [maxMultiplier, actualValue, setSelectedMultiplier]);

  if (isLoading) return <div className="bg-white py-3 px-4 text-black rounded-xs">Loading multiplier data...</div>;

  return (
    <div className="w-full pt-9 max-h-24 px-2 md:px-0">
      <div className="relative h-2 w-full cursor-pointer">
        <div className="mt-3.5 mr-0 -mb-2.5">
          <div className="mt-2.5 w-full">
            <div
              className="relative h-2 w-full cursor-pointer"
              ref={sliderRef}
              onMouseDown={handleMouseDown}
              onTouchStart={handleTouchStart}
            >
              <div className="absolute h-full w-full rounded-full border border-border-color">
                <div
                  className="absolute h-full rounded-full bg-gradient-to-r from-nav-button-hover to-pink"
                  style={{
                    width: `${calculateSliderPercentage(actualValue)}%`,
                  }}
                ></div>
              </div>
              <div
                className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 transition-colors duration-300 w-8 h-8 sm:w-[40px] sm:h-10"
                style={{
                  left: `${calculateSliderPercentage(actualValue)}%`,
                }}
              >
                <div className="bg-[#2c5475] absolute h-8 w-12 bottom-10 sm:bottom-12 left-5 -translate-x-1/2 text-primary text-sm py-1.5 px-2 rounded-[7.17px] transition-opacity duration-200 ease-in-out text-center after:content-[''] after:absolute after:-bottom-3.5 after:left-1/2 after:-translate-x-1/2 after:border-8 after:border-solid after:border-transparent after:border-t-[#2c5475] p-1">
                  {actualValue.toFixed(1)}
                </div>
                <img src={sliderThumb} className="h-full w-full" alt="slider thumb" draggable="false" />
              </div>
            </div>
          </div>
          <div className="w-full flex justify-between mt-5">
            {marks.map((mark, index) => (
              <div
                key={index}
                className={`flex flex-col gap-2 items-center w-4  ${actualValue === mark ? 'text-primary' : 'text-slider-gray'}`}
                style={{
                  left: `${calculateSliderPercentage(mark)}%`,
                  position: 'absolute',
                  transform: 'translateX(-50%)',
                }}
              >
                <div
                  className={`w-1 h-3 rounded-xl ${actualValue === mark ? 'bg-nav-button-hover' : 'bg-slider-gray'} `}
                />
                <span className="text-sm">{`x${mark}`}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MultiplierSelector;
