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
  // In Dev: Assume Backend is on port 5000 (standard flask/fastapi default)
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

export interface AuthUser {
  id: string;
  username: string;
  roles: string[];
  scopes?: string[];
  principal_type?: string;
  auth_provider?: string;
  is_active?: boolean;
  created_at?: number;
}

export interface AuthStatus {
  setup_required: boolean;
  oidc_enabled: boolean;
  authenticated: boolean;
  user: AuthUser | null;
  providers: string[];
  password_recommended_length: number;
}

export interface ManagedAccountBinding {
  user_id?: string;
  server_plugin_id: number;
  managed_account_id: string;
  created_at?: number;
}

export interface ExternalAccountBinding {
  id?: number;
  user_id: string;
  provider: string;
  category: 'streaming' | 'media_server';
  external_account_id: string;
  display_name: string;
  plugin_id?: number | null;
  created_at?: number;
}

export interface AvailableExternalAccount {
  provider: string;
  external_account_id: string;
  display_name: string;
  account_db_id?: number;
  plugin_id?: number | null;
  is_authenticated?: boolean;
}

export interface FamilyProfile {
  user_id: string;
  username: string;
  provider: string;
  external_account_id: string;
  display_name: string;
  is_self: boolean;
}

export interface ApiKeyRecord {
  id: string;
  user_id: string;
  name: string;
  key_prefix: string;
  api_key?: string;
  scopes: string[];
  expires_at?: number | null;
  created_at?: number;
  last_used_at?: number | null;
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // Request timeout (30 seconds)
  withCredentials: true, // Ensure HttpOnly cookies are sent with every request
});

/**
 * Utility to extract a cookie value by name
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

// Add a request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Inject Double-Submit CSRF Token from cookie into header
    const csrfToken = getCookie('csrf_token') || getCookie('echo_csrf');
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
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
      console.warn(
        `%c[EchoSync-Warning] Legacy components/routes detected: ${warning}`,
        'color: #ff3e00; font-weight: bold;'
      );
    }
    return response;
  },
  (error) => {
    const warning = error.response?.headers['x-echosync-warning'];
    if (warning) {
      console.warn(
        `%c[EchoSync-Warning] Legacy components/routes detected: ${warning}`,
        'color: #ff3e00; font-weight: bold;'
      );
    }
    // Handle global API errors
    if (error.response?.status === 401) {
      console.warn('[API] Unauthorized: Outbound Gateway Blocked.');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('es-auth-required'));
      }
    }
    console.error('API Error:', error.message || error);
    return Promise.reject(error);
  }
);

// ── Auth & First-Boot Setup API Methods ────────────────────────────────────

export async function getAuthStatus(): Promise<AuthStatus> {
  const response = await apiClient.get<AuthStatus>('/auth/status');
  return response.data;
}

export async function setupAdmin(username: string, password: string) {
  const response = await apiClient.post('/auth/setup', { username, password });
  return response.data;
}

export async function login(username: string, password: string) {
  const response = await apiClient.post('/auth/login', { username, password });
  return response.data;
}

export async function logout() {
  const response = await apiClient.post('/auth/logout');
  return response.data;
}

export async function getCurrentUser(): Promise<{ user: AuthUser }> {
  const response = await apiClient.get<{ user: AuthUser }>('/auth/me');
  return response.data;
}

export function getOidcLoginUrl(redirectUri?: string): string {
  const base = `${API_BASE_URL}/auth/oidc/login`;
  if (redirectUri) {
    return `${base}?redirect_uri=${encodeURIComponent(redirectUri)}`;
  }
  return base;
}

// ── Admin Users, Roles, Managed Accounts & API Keys ────────────────────────

export async function listUsers(): Promise<{ users: AuthUser[]; total: number }> {
  const response = await apiClient.get<{ users: AuthUser[]; total: number }>('/auth/users');
  return response.data;
}

export async function createUser(payload: {
  username: string;
  password?: string;
  roles?: string[];
  auth_provider?: string;
}): Promise<{ success: boolean; user: AuthUser }> {
  const response = await apiClient.post<{ success: boolean; user: AuthUser }>(
    '/auth/users',
    payload
  );
  return response.data;
}

export async function listRoles(): Promise<{
  roles: Array<{ id?: number; name: string; description?: string; permissions?: string[] }>;
  total: number;
}> {
  const response = await apiClient.get('/auth/roles');
  return response.data;
}

export async function assignUserRoles(
  userId: string,
  roles: string[]
): Promise<{ success: boolean; user: AuthUser }> {
  const response = await apiClient.put<{ success: boolean; user: AuthUser }>(
    `/auth/users/${encodeURIComponent(userId)}/roles`,
    { roles }
  );
  return response.data;
}

export async function listManagedAccounts(userId: string): Promise<{
  user_id: string;
  managed_accounts: ManagedAccountBinding[];
  total: number;
}> {
  const response = await apiClient.get(
    `/auth/users/${encodeURIComponent(userId)}/managed-accounts`
  );
  return response.data;
}

export async function assignManagedAccount(
  userId: string,
  serverPluginId: number,
  managedAccountId: string
): Promise<{ success: boolean; managed_accounts: ManagedAccountBinding[] }> {
  const response = await apiClient.post(
    `/auth/users/${encodeURIComponent(userId)}/managed-accounts`,
    {
      server_plugin_id: Number(serverPluginId),
      managed_account_id: String(managedAccountId),
    }
  );
  return response.data;
}

export async function removeManagedAccount(
  userId: string,
  serverPluginId: number,
  managedAccountId: string
): Promise<{ success: boolean }> {
  const response = await apiClient.delete(
    `/auth/users/${encodeURIComponent(userId)}/managed-accounts/${encodeURIComponent(
      String(serverPluginId)
    )}/${encodeURIComponent(managedAccountId)}`
  );
  return response.data;
}

export async function listApiKeys(
  userId?: string
): Promise<{ api_keys: ApiKeyRecord[]; total: number }> {
  const params = userId ? { user_id: userId } : undefined;
  const response = await apiClient.get<{ api_keys: ApiKeyRecord[]; total: number }>(
    '/auth/api-keys',
    { params }
  );
  return response.data;
}

export async function createApiKey(payload: {
  name: string;
  scopes?: string[];
  expires_at?: number | null;
}): Promise<{ success: boolean } & ApiKeyRecord> {
  const response = await apiClient.post('/auth/api-keys', payload);
  return response.data;
}

export async function deleteApiKey(keyId: string): Promise<{ success: boolean }> {
  const response = await apiClient.delete(`/auth/api-keys/${encodeURIComponent(keyId)}`);
  return response.data;
}

export async function listExternalAccounts(userId: string): Promise<{
  user_id: string;
  external_accounts: ExternalAccountBinding[];
  total: number;
}> {
  const response = await apiClient.get(
    `/auth/users/${encodeURIComponent(userId)}/external-accounts`
  );
  return response.data;
}

export async function bindExternalAccount(
  userId: string,
  payload: {
    provider: string;
    external_account_id: string;
    display_name?: string;
    category?: 'streaming' | 'media_server';
    plugin_id?: number | null;
  }
): Promise<{ success: boolean; external_accounts: ExternalAccountBinding[] }> {
  const response = await apiClient.post(
    `/auth/users/${encodeURIComponent(userId)}/external-accounts`,
    payload
  );
  return response.data;
}

export async function unbindExternalAccount(
  userId: string,
  provider: string,
  externalAccountId: string
): Promise<{ success: boolean; external_accounts: ExternalAccountBinding[] }> {
  const response = await apiClient.delete(
    `/auth/users/${encodeURIComponent(userId)}/external-accounts/${encodeURIComponent(
      provider
    )}/${encodeURIComponent(externalAccountId)}`
  );
  return response.data;
}

export async function listAvailableExternalAccounts(): Promise<{
  streaming: AvailableExternalAccount[];
  media_server: AvailableExternalAccount[];
}> {
  const response = await apiClient.get('/auth/external-accounts/available');
  return response.data;
}

export async function listFamilyProfiles(provider?: string): Promise<{
  my_profiles: FamilyProfile[];
  family_profiles: FamilyProfile[];
  default_target_user_id: string | null;
}> {
  const params = provider ? { provider } : undefined;
  const response = await apiClient.get('/auth/family-profiles', { params });
  return response.data;
}

export async function resetUserPassword(
  userId: string,
  password: string
): Promise<{ success: boolean }> {
  const response = await apiClient.put(`/auth/users/${encodeURIComponent(userId)}/password`, {
    password,
  });
  return response.data;
}

export async function deleteUser(userId: string): Promise<{ success: boolean }> {
  const response = await apiClient.delete(`/auth/users/${encodeURIComponent(userId)}`);
  return response.data;
}

// Attach helpers directly onto apiClient for convenience across components
Object.assign(apiClient, {
  getCookie,
  getAuthStatus,
  setupAdmin,
  login,
  logout,
  getCurrentUser,
  getOidcLoginUrl,
  listUsers,
  createUser,
  listRoles,
  assignUserRoles,
  listManagedAccounts,
  assignManagedAccount,
  removeManagedAccount,
  listExternalAccounts,
  bindExternalAccount,
  unbindExternalAccount,
  listAvailableExternalAccounts,
  listFamilyProfiles,
  resetUserPassword,
  deleteUser,
  listApiKeys,
  createApiKey,
  deleteApiKey,
});

export default apiClient;
