<script lang="ts">
  import { fade, fly } from 'svelte/transition';
  import { auth } from '../../stores/auth';
  import { feedback } from '../../stores/feedback';

  let {
    oidcEnabled = false,
    onLoginSuccess = () => {},
  } = $props();

  let username = $state('');
  let password = $state('');
  let showPassword = $state(false);
  let submitting = $state(false);
  let errorMessage = $state('');

  const canSubmit = $derived(
    username.trim().length > 0 && password.length > 0 && !submitting
  );

  async function handleLocalLogin(e: Event) {
    e.preventDefault();
    if (!canSubmit) return;

    submitting = true;
    errorMessage = '';
    try {
      await auth.login(username.trim(), password);
      feedback.addToast('Signed in to EchoSync', 'success');
      onLoginSuccess();
    } catch (err: any) {
      errorMessage = err?.message || 'Invalid username or password.';
    } finally {
      submitting = false;
    }
  }

  function handleOidcLogin() {
    const redirectUri = typeof window !== 'undefined' ? window.location.origin : undefined;
    auth.startOidcLogin(redirectUri);
  }
</script>

<div
  class="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto"
  style="background: radial-gradient(circle at 20% 20%, rgba(20, 184, 166, 0.12), transparent 40%), radial-gradient(circle at 80% 0%, rgba(14, 165, 233, 0.12), transparent 35%), var(--bg-canvas);"
  in:fade={{ duration: 180 }}
>
  <div
    class="w-full max-w-md rounded-2xl border p-6 sm:p-8 shadow-2xl"
    style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    in:fly={{ y: 16, duration: 220 }}
  >
    <div class="mb-6 text-center">
      <div
        class="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-3 font-black text-xl"
        style="background: rgba(20, 184, 166, 0.15); color: var(--color-primary); border: 1px solid rgba(20, 184, 166, 0.3);"
      >
        ES
      </div>
      <h1 class="text-2xl font-bold tracking-tight" style="color: var(--text-primary);">
        Sign in to EchoSync
      </h1>
      <p class="text-xs mt-1" style="color: var(--text-muted);">
        Music Sync &amp; Sovereign Library Control Plane
      </p>
    </div>

    {#if errorMessage}
      <div
        class="mb-5 p-3.5 rounded-xl text-xs font-medium border"
        style="background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.4); color: #fca5a5;"
        role="alert"
      >
        {errorMessage}
      </div>
    {/if}

    <form onsubmit={handleLocalLogin} class="space-y-4">
      <div>
        <label for="login-username" class="block text-xs font-semibold uppercase tracking-wider mb-1.5" style="color: var(--text-secondary);">
          Username
        </label>
        <input
          id="login-username"
          type="text"
          bind:value={username}
          required
          autocomplete="username"
          placeholder="Enter your username"
          class="input-field"
        />
      </div>

      <div>
        <label for="login-password" class="block text-xs font-semibold uppercase tracking-wider mb-1.5" style="color: var(--text-secondary);">
          Password or Passphrase
        </label>
        <div class="password-wrapper">
          <input
            id="login-password"
            type={showPassword ? 'text' : 'password'}
            bind:value={password}
            required
            autocomplete="current-password"
            placeholder="Enter your password"
            class="input-field pr-16"
          />
          <button
            type="button"
            class="toggle-visibility text-xs font-semibold"
            onclick={() => (showPassword = !showPassword)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? 'Hide' : 'Show'}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        class="w-full py-3 px-4 rounded-xl font-bold text-sm transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed mt-2"
        style="background-color: var(--color-primary); color: #020617;"
      >
        {submitting ? 'Signing In…' : 'Sign In'}
      </button>
    </form>

    {#if oidcEnabled || $auth.oidcEnabled}
      <div class="my-5 flex items-center gap-3">
        <div class="h-px flex-1" style="background-color: var(--border-subtle);"></div>
        <span class="text-[11px] uppercase tracking-wider font-semibold" style="color: var(--text-muted);">
          or continue with SSO
        </span>
        <div class="h-px flex-1" style="background-color: var(--border-subtle);"></div>
      </div>

      <button
        type="button"
        onclick={handleOidcLogin}
        class="w-full py-3 px-4 rounded-xl font-semibold text-sm transition-all active:scale-95 flex items-center justify-center gap-2.5 border"
        style="background-color: var(--bg-surface-elevated); border-color: rgba(20, 184, 166, 0.35); color: var(--text-primary);"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
        </svg>
        <span>Sign in with Authentik SSO</span>
      </button>
    {/if}
  </div>
</div>
