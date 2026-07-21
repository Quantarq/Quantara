import React, { useEffect, useId, useRef } from 'react';
import { Button } from '@/components/ui/custom-button/Button';
import useLockBodyScroll from '@/hooks/useLockBodyScroll';
import { cn } from '@/utils/cn';

/**
 * ActionModal — WCAG 2.2 AA compliant modal dialog.
 *
 * Per Issue #272 acceptance criteria:
 *   • role="dialog", aria-modal="true"
 *   • labelled with aria-labelledby pointing at the title element
 *   • described with aria-describedby pointing at the subtitle element
 *   • focus trap inside the dialog (Tab cycles across focusable elements)
 *   • Esc key closes the modal via cancelAction
 *   • focus is restored to the previously focused element on close
 */
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

  const titleId = useId();
  const subtitleId = useId();
  const panelRef = useRef(null);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    // Save the previously focused element and restore on close.
    previouslyFocusedRef.current = document.activeElement;

    const focusableSelector = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ].join(',');

    // Move focus into the modal on open.
    const firstFocusable = panelRef.current?.querySelector(focusableSelector);
    firstFocusable?.focus();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        if (!isLoading) cancelAction?.();
        return;
      }
      if (e.key !== 'Tab' || !panelRef.current) return;

      const focusables = Array.from(
        panelRef.current.querySelectorAll(focusableSelector)
      ).filter((el) => !el.hasAttribute('disabled'));
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus to the element that opened the modal.
      const previouslyFocused = previouslyFocusedRef.current;
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        previouslyFocused.focus();
      }
    };
  }, [isOpen, cancelAction, isLoading]);

  if (!isOpen) {
    return null;
  }
  return (
    <div
      className="fixed top-0 left-0 z-[55555] flex h-full w-full items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={cancelAction}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={subtitleId}
    >
      <div
        ref={panelRef}
        data-focus-managed="true"
        className="shadow-primary-color flex items-center justify-center overflow-hidden text-white"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex w-[330px] flex-col gap-[18px] rounded-2xl text-center md:w-full md:max-w-[700px] md:gap-6">
          <div className="border-nav-divider-bg bg-bg h-fit rounded-2xl border p-6 py-4 pt-4 text-center text-sm md:rounded-2xl">
            <div
              id={titleId}
              className="text-primary mb-6 w-full border-b border-b-[rgba(255,255,255,0.1)] px-[10px] py-[10px] text-center text-base text-[13px] sm:mb-[14px] sm:py-[6px] md:mb-4 md:pb-4"
            >
              {title}
            </div>
            <div className="grid min-h-28 place-content-center px-2">
              <h2 id={subtitleId} className={cn('mx-auto mb-4 text-sm font-semibold md:text-2xl', content.length && 'px-0 py-[55px]')}>
                {subTitle}
              </h2>
              {content.map((line, i) => (
                <p className="mx-auto mt-0 mb-3 max-w-96 text-base leading-6" key={i}>
                  {line}
                </p>
              ))}
            </div>
          </div>
          <div className="flex justify-between gap-2 md:gap-4">
            <Button variant="secondary" size="md" onClick={cancelAction} disabled={isLoading}>
              {cancelLabel}
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={submitAction}
              disabled={isLoading}
              aria-busy={isLoading}
            >
              {isLoading ? 'Loading...' : submitLabel}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActionModal;
