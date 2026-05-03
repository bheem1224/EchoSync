/**
 * Core API fetch wrapper for EchoSync
 * Enforces HttpOnly cookie persistence and Double-Submit CSRF protection.
 */

import { API_BASE_URL } from '../api/client';

/**
 * Extracts a cookie value by name from document.cookie
 */
export function getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null;
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop()?.split(';').shift() || null;
    }
    return null;
}

/**
 * Standard fetch wrapper that automatically includes:
 * 1. credentials: 'same-origin' (for HttpOnly auth cookie)
 * 2. X-Echo-CSRF header (from echo_csrf cookie)
 */
export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    
    // Ensure credentials are sent for HttpOnly cookies
    options.credentials = options.credentials || 'same-origin';
    
    // Inject CSRF header from cookie
    const csrfToken = getCookie('echo_csrf');
    if (csrfToken) {
        options.headers = {
            ...options.headers,
            'X-Echo-CSRF': csrfToken
        };
    }

    const response = await fetch(url, options);

    if (response.status === 401) {
        console.warn('[API] 401 Unauthorized: Outbound Gateway Blocked.');
        // Optional: Trigger auth state reset or redirect to login
    }

    return response;
}

export default apiFetch;
