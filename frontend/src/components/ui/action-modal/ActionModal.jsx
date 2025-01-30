import React from 'react';
import './actionModal.css';
import { Button } from '@/components/ui/custom-button/Button';
import useLockBodyScroll from '@/hooks/useLockBodyScroll';

const ActionModal = ({
  isOpen,
  title,
  subTitle,
  content = [],
  cancelLabel = 'Cancel',
  cancelAction,
  submitLabel,
  submitAction,
  isLoading = false,
}) => {
  useLockBodyScroll(isOpen);

  if (!isOpen) {
    return null;
  }
  return (
    <div className="flex items-center justify-center fixed top-0 left-0 w-full h-full backdrop-blur z-[9999]" onClick={cancelAction}> // bg spinner-bg
      <div className="lg:w-[580px] max-[320px]:w-[300px] sm:w-[500px] flex items-center justify-center overflow-hidden  shadow-primary-color" onClick={(e) => e.stopPropagation()}>
        <div className="rounded-2xl ma-w-[700px] flex flex-col gap-6 text-center sm:w-[330px] sm:gap-[18px] max-[300px]:w-[300px]">
          <div className="text-center py-4 px-6 border rounded-3xl h-[300px] lg:py-4 lg:px-0 lg:rounded-2xl lg:h-[280px] sm:pt-4 sm:rounded-2xl sm:h-[200px]"> /// bg
            <div className="lg:text-sm lg:pb-2 sm:text-[13px] sm:p-[6px] sm:mb-[14px] lg:mb-2 text-primary text-center text-base p-[10px] mb-6 ">{title}</div> //rgb
            <h2 className={`${!content.length && 'sm:py-[43px] p-y-[55px] px-0 lg:py-[68px]'} text-primary text-2xl font-semibold leading-[125%] max-w-[400px] mx-auto mt-0 mb-4 font lg:text-xl lg:mb-[10px] sm:text-sm sm:mb-[10px]`}>{subTitle}</h2> //font
            {content.map((content, i) => (
              <p className='sm:text-xs text-[#fdfdfd] text-base max-w-[380px] leading-[1.5] mt-0 mx-auto mb-3' key={i}>{content}</p>
            ))}
          </div>
          <div className="flex gap-4 lg:gap-[14px] sm:gap-2 sm:justify-center">
            <Button variant="secondary" size="md" className="modal-btn" onClick={cancelAction} disabled={isLoading}>
              {cancelLabel}
            </Button>
            <Button variant="primary" size="md" onClick={submitAction} disabled={isLoading}>
              {isLoading ? 'Loading...' : submitLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActionModal;
