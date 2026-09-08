import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// `new URL(..., import.meta.url)` rather than `node:path` + `__dirname`, so the
// config needs no @types/node in a project that otherwise targets the browser.
const srcDir = new URL('./src', import.meta.url).pathname;

export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves a project page from a sub-path, so every asset URL has
  // to be prefixed with the repository name. Override at build time for a user
  // page or a custom domain, both of which serve from the root:
  //   npm run build -- --base=/
  base: '/Py-Tutor/',
  resolve: {
    alias: { '@': srcDir },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Monaco is large; keeping it in its own chunk means a lesson page that
        // does not open the editor never downloads it.
        manualChunks: {
          monaco: ['@monaco-editor/react'],
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
});
