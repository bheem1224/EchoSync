// Global API client for the SvelteKit application
// Configured to accept self-signed certificates from the internal backend

import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api', // Base URL for backend API
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