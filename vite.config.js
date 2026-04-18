import { defineConfig } from 'vite';

export default defineConfig({
  root: 'src',
  base: './',
  publicDir: '../assets',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  optimizeDeps: {
    include: ['pixi.js'],
  },
});
