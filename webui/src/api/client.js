// Global API client for the SvelteKit application
// Configured to accept self-signed certificates from the internal backend

import axios from 'axios';

// Detect backend protocol at runtime
async function detectBackendProtocol() {
  try {
    // Try HTTPS first (default), fall back to HTTP if fails
    const protocols = ['https', 'http'];
    
    for (const protocol of protocols) {
      try {
        const response = await axios.get(`${protocol}://localhost:8000/api/backend-info`, {
          timeout: 2000,
          validateStatus: () => true, // Accept any status to detect connectivity
          httpsAgent: { rejectUnauthorized: false }, // Accept self-signed certs
        });
        
        if (response.status === 200 && response.data?.protocol) {
          console.log(`[API] Backend detected as ${response.data.protocol.toUpperCase()}`);
          return response.data.protocol;
        }
      } catch (e) {
        // Protocol failed, try next
        continue;
      }
    }
    
    // Default to HTTPS if detection fails
    console.warn('[API] Could not detect backend protocol, defaulting to HTTPS');
    return 'https';
  } catch (e) {
    console.warn('[API] Backend protocol detection error, defaulting to HTTPS:', e.message);
    return 'https';
  }
}

// Create API client with protocol detection
const apiClient = axios.create({
  baseURL: '/api', // Base URL for backend API (proxied through Vite)
  timeout: 10000, // Request timeout (10 seconds)
});

// Add a request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add authorization token or other headers if needed
    // Example: config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle self-signed certificate errors from internal backend
    if (error.code === 'EPROTO' || error.message?.includes('self signed certificate')) {
      console.warn('[API] Self-signed cert from internal backend (expected for internal HTTPS)');
    }
    
    // Handle global API errors
    console.error('API Error:', error.message || error);
    return Promise.reject(error);
  }
);

export default apiClient;
export { detectBackendProtocol };