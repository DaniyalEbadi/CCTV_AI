import { defineConfig } from 'vite';
import { resolve } from 'path';

// https://vitejs.dev/config
export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@app': resolve(__dirname, './src'),
      '@shared': resolve(__dirname, './src/types'),
      '@main': resolve(__dirname, './src/main'),
      '@preload': resolve(__dirname, './src/preload'),
      '@bridges': resolve(__dirname, './src/preload/bridges'),
      '@renderer': resolve(__dirname, './src/renderer'),
      '@i18n': resolve(__dirname, './src/i18n'),
    },
  },
});
