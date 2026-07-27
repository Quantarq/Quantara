import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ActionModal from '@/components/ui/action-modal/ActionModal';

describe('ActionModal a11y (issue #272)', () => {
  // Each test gets its own mock so previous tests' calls don't pollute
  // the next assertion (a regression of the original failure).
  const makeBaseProps = () => ({
    isOpen: true,
    title: 'Confirm action',
    subTitle: 'Are you sure you want to proceed?',
    cancelLabel: 'No',
    submitLabel: 'Yes',
    cancelAction: vi.fn(),
    submitAction: vi.fn(),
  });

  it('renders with role=dialog + aria-modal + aria-labelledby/describedby', () => {
    render(<ActionModal {...makeBaseProps()} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby');
    expect(dialog).toHaveAttribute('aria-describedby');
  });

  it('renders title and subtitle as the labelledby / describedby targets', () => {
    render(<ActionModal {...makeBaseProps()} />);
    expect(screen.getByText('Confirm action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument();
  });

  it('closes on Escape (calls cancelAction)', () => {
    const props = makeBaseProps();
    render(<ActionModal {...props} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(props.cancelAction).toHaveBeenCalledTimes(1);
  });

  it('does not close on Escape while loading', () => {
    const props = makeBaseProps();
    render(<ActionModal {...props} isLoading />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(props.cancelAction).not.toHaveBeenCalled();
  });

  it('traps Tab focus inside the dialog', () => {
    render(<ActionModal {...makeBaseProps()} />);
    const submit = screen.getByRole('button', { name: 'Yes' });
    const cancel = screen.getByRole('button', { name: 'No' });
    submit.focus();
    fireEvent.keyDown(submit, { key: 'Tab' });
    // After Tab from the last focusable, focus should wrap to the first.
    expect(document.activeElement).toBe(cancel);
  });
});
