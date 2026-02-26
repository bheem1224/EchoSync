// Global API client for the SvelteKit application
// Configured to be protocol agnostic and support decoupled backend

import axios from 'axios';

// Determine the base URL dynamically
// 1. Check for explicit ENV override first (for docker/custom setups)
const ENV_API_URL = import.meta.env.VITE_API_URL;

// 2. Dynamic Fallback
let determinedBaseURL = '/api'; // Default for Prod (relative path)

if (ENV_API_URL) {
  determinedBaseURL = ENV_API_URL;
} else if (import.meta.env.DEV) {
  // In Dev: Assume Backend is on port 5000 (standard flask default)
  // Check if running on client side
  if (typeof window !== 'undefined') {
    // Protocol agnostic: use same protocol as current page (http/https)
    determinedBaseURL = `${window.location.protocol}//${window.location.hostname}:5000/api`;
  } else {
    // SSR Fallback in Dev
    determinedBaseURL = 'http://localhost:5000/api';
  }
}

console.log(`[API] Initializing client with baseURL: ${determinedBaseURL}`);

export const API_BASE_URL = determinedBaseURL;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
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
    // Handle global API errors
    console.error('API Error:', error.message || error);
    return Promise.reject(error);
  }
);

export default apiClient;
