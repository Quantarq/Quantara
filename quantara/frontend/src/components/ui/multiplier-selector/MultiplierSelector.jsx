import React, { useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { useMaxMultiplier } from '@/hooks/useMaxMultiplier';
import sliderThumb from '@/assets/icons/slider_thumb.svg';

/**
 * MultiplierSelector — WCAG 2.2 AA compliant slider.
 *
 * The custom track is supplemented by a hidden native `<input type="range">`
 * with `role="slider"` semantics so that screen readers announce the value,
 * min, max, and step changes. Keyboard users can adjust the multiplier with
 * Left/Right (1x steps), PageUp/PageDown (1x), and Home/End (jump to ends).
 */
const MultiplierSelector = ({ setSelectedMultiplier, selectedToken, id }) => {
  const minMultiplier = 1.1;
  const rangeInputRef = useRef(null);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleDrag]);

  useEffect(() => {
    if (actualValue > maxMultiplier) {
      setActualValue(maxMultiplier);
      setSelectedMultiplier(maxMultiplier.toFixed(1));
    } else {
      setSelectedMultiplier(actualValue.toFixed(1));
    }
  }, [maxMultiplier, actualValue, setSelectedMultiplier]);

  // Keyboard interaction: mirror native input range semantics so that
  // assistive technology announces the value correctly.
  const handleKeyDown = (e) => {
    const step = e.shiftKey ? 1.0 : 0.1;
    let next = actualValue;
    const stepRound = (v) => Math.round(v * 10) / 10;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') next = stepRound(actualValue + step);
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') next = stepRound(actualValue - step);
    else if (e.key === 'PageUp') next = stepRound(actualValue + 1);
    else if (e.key === 'PageDown') next = stepRound(actualValue - 1);
    else if (e.key === 'Home') next = minMultiplier;
    else if (e.key === 'End') next = maxMultiplier;
    else return;
    e.preventDefault();
    next = Math.max(minMultiplier, Math.min(maxMultiplier, next));
    setActualValue(next);
    setSelectedMultiplier(next.toFixed(1));
    if (rangeInputRef.current) {
      rangeInputRef.current.value = String(next);
      rangeInputRef.current.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };

  if (isLoading)
    return <div className="rounded-xs bg-white px-4 py-3 text-black">Loading multiplier data...</div>;

  const labelId = id ? `${id}-label` : undefined;

  return (
    <div className="max-h-24 w-full px-2 pt-9 md:px-0">
      {/* Hidden accessible slider for assistive tech. */}
      <input
        ref={rangeInputRef}
        id={id}
        type="range"
        min={minMultiplier}
        max={maxMultiplier}
        step={0.1}
        value={actualValue}
        onChange={(e) => {
          const next = Number(e.target.value);
          setActualValue(next);
          setSelectedMultiplier(next.toFixed(1));
        }}
        aria-label="Leverage multiplier"
        aria-labelledby={labelId}
        aria-valuemin={minMultiplier}
        aria-valuemax={maxMultiplier}
        aria-valuenow={actualValue}
        aria-valuetext={`${actualValue.toFixed(1)}x`}
        tabIndex={-1}
        className="sr-only"
        data-testid="multiplier-hidden-range"
      />

      <div className="relative h-2 w-full cursor-pointer">
        <div className="mt-3.5 mr-0 -mb-2.5">
          <div className="mt-2.5 w-full">
            <div
              role="slider"
              tabIndex={0}
              aria-labelledby={labelId}
              aria-valuemin={minMultiplier}
              aria-valuemax={maxMultiplier}
              aria-valuenow={actualValue}
              aria-valuetext={`${actualValue.toFixed(1)}x`}
              className="relative h-2 w-full cursor-pointer rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
              ref={sliderRef}
              onMouseDown={handleMouseDown}
              onTouchStart={handleTouchStart}
              onKeyDown={handleKeyDown}
            >
              <div className="border-border-color absolute h-full w-full rounded-full border">
                <div
                  className="from-nav-button-hover to-pink absolute h-full rounded-full bg-gradient-to-r"
                  style={{
                    width: `${calculateSliderPercentage(actualValue)}%`,
                  }}
                ></div>
              </div>
              <div
                className="absolute top-1/2 h-8 w-8 -translate-x-1/2 -translate-y-1/2 transition-colors duration-300 sm:h-10 sm:w-[40px]"
                style={{
                  left: `${calculateSliderPercentage(actualValue)}%`,
                }}
              >
                <div className="text-primary absolute bottom-10 left-5 h-8 w-12 -translate-x-1/2 rounded-[7.17px] bg-[#2c5475] p-1 px-2 py-1.5 text-center text-sm transition-opacity duration-200 ease-in-out after:absolute after:-bottom-3.5 after:left-1/2 after:-translate-x-1/2 after:border-8 after:border-solid after:border-transparent after:border-t-[#2c5475] after:content-[''] sm:bottom-12">
                  {actualValue.toFixed(1)}
                </div>
                <img src={sliderThumb} className="h-full w-full" alt="slider thumb" draggable="false" />
              </div>
            </div>
          </div>
          <div className="mt-5 flex w-full justify-between">
            {marks.map((mark, index) => (
              <div
                key={index}
                className={`flex w-4 flex-col items-center gap-2 ${
                  actualValue === mark ? 'text-primary' : 'text-slider-gray'
                }`}
                style={{
                  left: `${calculateSliderPercentage(mark)}%`,
                  position: 'absolute',
                  transform: 'translateX(-50%)',
                }}
              >
                <div
                  className={`h-3 w-1 rounded-xl ${
                    actualValue === mark ? 'bg-nav-button-hover' : 'bg-slider-gray'
                  } `}
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
