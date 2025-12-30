import { sveltekit } from '@sveltejs/kit/vite';

const config = {
  plugins: [sveltekit()],
  server: {
    port: 5173,
    strictPort: false,
    // Proxy API requests to backend
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // HTTP for dev (HTTPS in production)
        changeOrigin: true,
        ws: false
      }
    }
  },
  optimizeDeps: {
    include: [] // Add dependencies here if needed
  }
};

export default config;