import React from 'react';
import './button.css';

export const Button = ({ variant = 'primary', size = 'md', className = '', children, ...props }) => {
  const buttonClasses = ['button', `button--${variant}`, `button--${size}`, className].filter(Boolean).join(' ');

  return (
    <button className={buttonClasses} {...props} style={{outline: "none", backgroundColor: "#120721" }} >
      {children}
    </button>
  );
};
