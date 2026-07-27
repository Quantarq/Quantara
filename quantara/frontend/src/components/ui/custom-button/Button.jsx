import React from 'react';
import { cva } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const buttonVariants = cva(
  [
    'relative cursor-pointer font-semibold rounded-[8px]',
    'flex justify-center items-center text-center text-sm h-[60px]',
    'transition-all duration-200 ease-in-out',
  ],
  {
    variants: {
      variant: {
        primary: [
          'text-white bg-transparent',
          'relative p-[1px] overflow-hidden',
          'before:absolute before:inset-0',
          'before:rounded-[8px]',
          'before:bg-gradient-to-r before:from-brand before:to-pink',
          'before:transition-all before:duration-300 before:ease-in-out',
          'enabled:hover:before:bg-gradient-to-r enabled:hover:before:from-pink enabled:hover:before:to-brand',
          'after:absolute after:inset-[1px]',
          'after:rounded-[7px]',
          'after:bg-bg',
          'active:translate-y-[1px] disabled:active:transform-none',
        ],
        secondary: [
          'text-white bg-transparent',
          'border border-light-purple border-solid rounded-[8px]',
          'transition-colors duration-300 ease-in-out',
          'enabled:hover:border-midnight-purple-hover',
          'active:translate-y-[1px] disabled:active:transform-none',
          'px-6 py-4',
        ],
      },
      size: {
        lg: 'w-full md:w-[642px]',
        md: 'w-[167px] md:w-[309px]',
        sm: 'w-[167px]',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

/**
 * Quantara Button component (WCAG 2.2 AA compliant).
 *
 * - Always renders a `<button type="button">` by default so accidental form
 *   submits don't happen; pages can override with `type="submit"`.
 * - Uses `focus-visible:ring-2 ring-brand ring-offset-2 ring-offset-bg` so the
 *   keyboard focus indicator has a ≥3:1 contrast ratio against the dark
 *   base background color.
 * - Relies on `aria-disabled` + `disabled` so screen readers correctly
 *   announce the disabled state.
 */
export const Button = React.forwardRef(
  (
    {
      className,
      variant,
      size,
      children,
      type = 'button',
      'aria-busy': ariaBusy,
      'aria-label': ariaLabel,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        aria-busy={ariaBusy}
        aria-label={ariaLabel}
        className={cn(
          buttonVariants({ variant, size, className }),
          // Suppress the global :focus-visible ring (from globals.css)
          // and use a high-contrast layered ring with offset instead.
          'focus:outline-none',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
          'focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          // Disable hover/cursor affordances when the element is disabled.
          'disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:before:bg-gradient-to-r disabled:hover:before:from-brand disabled:hover:before:to-pink'
        )}
        {...props}
      >
        <span className="relative z-10 py-4 md:px-6">{children}</span>
      </button>
    );
  }
);

Button.displayName = 'Button';
