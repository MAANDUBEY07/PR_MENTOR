import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  // GitHub Pages serves this repository at /PR_MENTOR/, not at the domain root.
  base: '/PR_MENTOR/',
  plugins: [react()],
});
