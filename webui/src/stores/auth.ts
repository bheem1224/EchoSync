import { writable } from 'svelte/store';
import {
  getAuthStatus,
  setupAdmin,
  login as apiLogin,
  logout as apiLogout,
  getOidcLoginUrl,
  type AuthUser,
} from '../api/client';

export interface AuthStoreState {
  loaded: boolean;
  loading: boolean;
  setupRequired: boolean;
  oidcEnabled: boolean;
  authenticated: boolean;
  user: AuthUser | null;
  providers: string[];
  passwordRecommendedLength: number;
  error: string | null;
}

const initialState: AuthStoreState = {
  loaded: false,
  loading: false,
  setupRequired: false,
  oidcEnabled: false,
  authenticated: false,
  user: null,
  providers: ['local'],
  passwordRecommendedLength: 15,
  error: null,
};

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthStoreState>(initialState);

  async function refresh() {
    update((s) => ({ ...s, loading: true, error: null }));
    try {
      const status = await getAuthStatus();
      update((s) => ({
        ...s,
        loaded: true,
        loading: false,
        setupRequired: Boolean(status.setup_required),
        oidcEnabled: Boolean(status.oidc_enabled),
        authenticated: Boolean(status.authenticated),
        user: status.user || null,
        providers: Array.isArray(status.providers) ? status.providers : ['local'],
        passwordRecommendedLength: status.password_recommended_length || 15,
        error: null,
      }));
      return status;
    } catch (err: any) {
      update((s) => ({
        ...s,
        loaded: true,
        loading: false,
        error: err?.response?.data?.detail || err?.message || 'Failed to check auth status',
      }));
      return null;
    }
  }

  async function setup(username: string, password: string) {
    update((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await setupAdmin(username, password);
      update((s) => ({
        ...s,
        loaded: true,
        loading: false,
        setupRequired: false,
        authenticated: true,
        user: data.user || null,
        error: null,
      }));
      return { success: true, user: data.user };
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'First-boot setup failed';
      update((s) => ({ ...s, loading: false, error: msg }));
      throw new Error(msg);
    }
  }

  async function login(username: string, password: string) {
    update((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await apiLogin(username, password);
      update((s) => ({
        ...s,
        loaded: true,
        loading: false,
        setupRequired: false,
        authenticated: true,
        user: data.user || null,
        error: null,
      }));
      return { success: true, user: data.user };
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Invalid username or password';
      update((s) => ({ ...s, loading: false, error: msg }));
      throw new Error(msg);
    }
  }

  async function logout() {
    try {
      await apiLogout();
    } catch (e) {
      console.warn('[auth] Logout warning:', e);
    }
    await refresh();
  }

  function startOidcLogin(redirectUri?: string) {
    if (typeof window !== 'undefined') {
      window.location.href = getOidcLoginUrl(redirectUri);
    }
  }

  return {
    subscribe,
    set,
    update,
    refresh,
    setup,
    login,
    logout,
    startOidcLogin,
  };
}

export const auth = createAuthStore();
export default auth;
