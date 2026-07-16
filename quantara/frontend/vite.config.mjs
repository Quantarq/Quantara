import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import svgr from 'vite-plugin-svgr';
import EnvironmentPlugin from 'vite-plugin-environment';
import tsconfigPaths from 'vite-tsconfig-paths';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  server: {
    port: 3000,
  },
  plugins: [
    // tsconfigPaths reads path aliases from tsconfig.json so @/* resolves
    // consistently in both Vite's dev server / build and tsc type-checking.
    tsconfigPaths(),
    react(),
    svgr(),
    EnvironmentPlugin('all'),
    tailwindcss(),
  ],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.js'],
    include: ['**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    alias: {
      '@': path.resolve(__dirname, './src'),
      '^src/(.*)$': './src/$1',
      '\\.svg\\?react$': './test/__mocks__/svgMock.js',
      '\\.svg$': './test/__mocks__/svgMock.js',
      '\\.css$': './test/__mocks__/styleMock.js',
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
