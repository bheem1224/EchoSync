import { sveltekit } from '@sveltejs/kit/vite';

const config = {
  plugins: [sveltekit()],
  server: {
    port: 5173,
    strictPort: false,
    // Proxy API requests to backend
    proxy: {
      '/api': {
        target: 'https://localhost:8000', // HTTPS self-signed
        changeOrigin: true,
        secure: false,
        ws: false
      }
    }
  },
  optimizeDeps: {
    include: [] // Add dependencies here if needed
  }
};

export default config;