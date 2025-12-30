import { defineConfig } from "vite";
import { resolve } from "path";
// eslint-disable-next-line import/no-unresolved
import tailwindcss from "@tailwindcss/vite";
// eslint-disable-next-line import/no-unresolved
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@app': resolve(__dirname, './src'),
      '@shared': resolve(__dirname, './src/types'),
      '@renderer': resolve(__dirname, './src/renderer'),
      '@components': resolve(__dirname, './src/renderer/components'),
      '@pages': resolve(__dirname, './src/renderer/pages'),
      '@ui': resolve(__dirname, './src/renderer/ui'),
      '@context': resolve(__dirname, './src/renderer/context'),
      '@constants': resolve(__dirname, './src/renderer/constants'),
      '@i18n': resolve(__dirname, './src/i18n'),
    },
  },
});
