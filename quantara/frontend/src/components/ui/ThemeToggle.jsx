import React from 'react';
import { useTheme } from '@/context/ThemeContext';

export const ThemeToggle = () => {
  const { theme, setThemeMode } = useTheme();

  return (
    <select
      value={theme}
      onChange={(e) => setThemeMode(e.target.value)}
      className="bg-transparent border border-border-light dark:border-border-lighter text-primary p-2 rounded cursor-pointer"
    >
      <option value="system">System</option>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
  );
};
