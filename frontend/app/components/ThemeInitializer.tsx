'use client';

import { useEffect } from 'react';

export default function ThemeInitializer() {
  useEffect(() => {
    // Initialize theme on client-side only
    const initializeTheme = () => {
      try {
        const colorScheme = localStorage.getItem('mui-color-scheme') || 'dark';
        document.documentElement.setAttribute('data-mui-color-scheme', colorScheme);
        document.documentElement.style.colorScheme = colorScheme;
      } catch (e) {
        // Fallback to dark mode
        document.documentElement.setAttribute('data-mui-color-scheme', 'dark');
        document.documentElement.style.colorScheme = 'dark';
      }
    };

    initializeTheme();
  }, []);

  return null;
}