import React, { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'system';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const updateClasses = () => {
      const isDark = theme === 'dark' || (theme === 'system' && mediaQuery.matches);
      if (isDark) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };

    updateClasses();

    const handleSystemThemeChange = () => {
      if (theme === 'system') {
        updateClasses();
      }
    };

    mediaQuery.addEventListener('change', handleSystemThemeChange);
    localStorage.setItem('theme', theme);

    return () => mediaQuery.removeEventListener('change', handleSystemThemeChange);
  }, [theme]);

  const setThemeMode = (mode) => {
    setTheme(mode);
  };

  return (
    <ThemeContext.Provider value={{ theme, setThemeMode }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
