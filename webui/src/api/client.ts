// Global API client for the SvelteKit application
// Configured to be protocol agnostic and support decoupled backend

import axios from 'axios';

// Determine the base URL dynamically
// 1. Check for explicit ENV override first (for docker/custom setups)
const ENV_API_URL = import.meta.env.VITE_API_URL;

// 2. Dynamic Fallback
let determinedBaseURL = '/api/v1'; // Default for Prod (relative path)

if (ENV_API_URL) {
  determinedBaseURL = ENV_API_URL;
} else if (import.meta.env.DEV) {
  // In Dev: Assume Backend is on port 5000 (standard flask default)
  // Check if running on client side
  if (typeof window !== 'undefined') {
    // Protocol agnostic: use same protocol as current page (http/https)
    determinedBaseURL = `${window.location.protocol}//${window.location.hostname}:5000/api/v1`;
  } else {
    // SSR Fallback in Dev
    determinedBaseURL = 'http://localhost:5000/api/v1';
  }
}

console.log(`[API] Initializing client with baseURL: ${determinedBaseURL}`);

export const API_BASE_URL = determinedBaseURL;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // Request timeout (30 seconds)
  withCredentials: true, // Ensure HttpOnly cookies are sent with every request
});

/**
 * Utility to extract a cookie value by name
 */
function getCookie(name) {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// Add a request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Inject Double-Submit CSRF Token from cookie into header
    const csrfToken = getCookie('echo_csrf');
    if (csrfToken) {
      config.headers['X-Echo-CSRF'] = csrfToken;
    }
    
    // Authorization: Bearer logic removed - handled by HttpOnly echo_auth cookie
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor
apiClient.interceptors.response.use(
  (response) => {
    const warning = response?.headers['x-echosync-warning'];
    if (warning) {
      console.warn(`%c[EchoSync-Warning] Legacy components/routes detected: ${warning}`, 'color: #ff3e00; font-weight: bold;');
    }
    return response;
  },
  (error) => {
    const warning = error.response?.headers['x-echosync-warning'];
    if (warning) {
      console.warn(`%c[EchoSync-Warning] Legacy components/routes detected: ${warning}`, 'color: #ff3e00; font-weight: bold;');
    }
    // Handle global API errors
    if (error.response?.status === 401) {
       console.warn('[API] Unauthorized: Outbound Gateway Blocked.');
       // Optional: Redirect to login or trigger auth store reset
    }
    console.error('API Error:', error.message || error);
    return Promise.reject(error);
  }
);

export default apiClient;
