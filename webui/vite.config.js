import { sveltekit } from '@sveltejs/kit/vite';
import { readFileSync } from 'fs';
import { resolve } from 'path';

// Detect backend protocol from parent .env file or default to HTTPS
function getBackendProtocol() {
  try {
    const envPath = resolve(__dirname, '../.env');
    const envContent = readFileSync(envPath, 'utf-8');
    
    // Check if DISABLE_INTERNAL_HTTPS or DEV_MODE are set to true
    const disableHttps = envContent.includes('DISABLE_INTERNAL_HTTPS=true');
    const devMode = envContent.includes('DEV_MODE=true');
    
    if (disableHttps || devMode) {
      console.log('[Vite] Backend detected as HTTP (DEV_MODE or DISABLE_INTERNAL_HTTPS=true)');
      return 'http';
    }
    
    console.log('[Vite] Backend detected as HTTPS (default)');
    return 'https';
  } catch (e) {
    console.log('[Vite] Could not read .env, defaulting backend to HTTPS');
    return 'https';
  }
}

const backendProtocol = getBackendProtocol();
const backendUrl = `${backendProtocol}://localhost:8000`;

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