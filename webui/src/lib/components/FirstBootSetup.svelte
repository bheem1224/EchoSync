<script lang="ts">
  import { fade, fly } from 'svelte/transition';
  import { auth } from '../../stores/auth';
  import { feedback } from '../../stores/feedback';

  let { onSetupComplete = () => {} } = $props();

  let username = $state('admin');
  let password = $state('');
  let confirmPassword = $state('');
  let showPassword = $state(false);
  let submitting = $state(false);
  let errorMessage = $state('');

  // NIST SP 800-63B-4 password policy metrics:
  // - Apply Unicode NFKC normalization without stripping spaces
  // - Min 8 characters
  // - 15+ characters recommended indicator
  // - 64+ character passphrases with spaces/Unicode supported
  // - Zero composition restrictions (no forced uppercase/digits/symbols)
  const normalizedPassword = $derived(password ? password.normalize('NFKC') : '');
  const charCount = $derived(Array.from(normalizedPassword).length);
  const meetsMinimum = $derived(charCount >= 8);
  const meetsRecommended = $derived(charCount >= 15);
  const isPassphraseTier = $derived(charCount >= 64);
  const withinMaxLength = $derived(charCount <= 512);
  const passwordsMatch = $derived(password.length > 0 && password === confirmPassword);

  const strengthLabel = $derived.by(() => {
    if (charCount === 0) return 'Enter a password or passphrase';
    if (charCount < 8) return `Too short (${charCount}/8 minimum)`;
    if (charCount >= 64) return 'Vault-Grade Passphrase (64+ chars)';
    if (charCount >= 15) return 'Recommended Passphrase Length (15+ chars)';
    return 'Meets 8-character minimum (15+ recommended)';
  });

  const strengthTier = $derived.by(() => {
    if (charCount === 0) return 'empty';
    if (charCount < 8) return 'invalid';
    if (charCount >= 64) return 'passphrase';
    if (charCount >= 15) return 'recommended';
    return 'minimum';
  });

  const canSubmit = $derived(
    username.trim().length > 0 &&
      meetsMinimum &&
      withinMaxLength &&
      passwordsMatch &&
      !submitting
  );

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if (!canSubmit) return;

    submitting = true;
    errorMessage = '';
    try {
      await auth.setup(username.trim(), password);
      feedback.addToast('Administrator account created', 'success');
      onSetupComplete();
    } catch (err: any) {
      errorMessage = err?.message || 'Failed to complete first-boot setup.';
    } finally {
      submitting = false;
    }
  }
</script>

<div
  class="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto"
  style="background: radial-gradient(circle at 20% 20%, rgba(20, 184, 166, 0.12), transparent 40%), radial-gradient(circle at 80% 0%, rgba(14, 165, 233, 0.12), transparent 35%), var(--bg-canvas);"
  in:fade={{ duration: 180 }}
>
  <div
    class="w-full max-w-lg rounded-2xl border p-6 sm:p-8 shadow-2xl"
    style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    in:fly={{ y: 16, duration: 220 }}
  >
    <div class="mb-6">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider mb-3"
           style="background: rgba(20, 184, 166, 0.14); color: var(--color-primary); border: 1px solid rgba(20, 184, 166, 0.3);">
        <span>First-Boot Initialization</span>
      </div>
      <h1 class="text-2xl font-bold tracking-tight" style="color: var(--text-primary);">
        Welcome to EchoSync
      </h1>
      <p class="text-sm mt-1.5" style="color: var(--text-muted);">
        Create the primary local administrator account to secure your server and unlock the control plane.
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

    <form onsubmit={handleSubmit} class="space-y-5">
      <div>
        <label for="setup-username" class="block text-xs font-semibold uppercase tracking-wider mb-2" style="color: var(--text-secondary);">
          Administrator Username
        </label>
        <input
          id="setup-username"
          type="text"
          bind:value={username}
          required
          minlength="1"
          maxlength="128"
          autocomplete="username"
          placeholder="admin"
          class="input-field"
        />
      </div>

      <div>
        <div class="flex items-center justify-between mb-2">
          <label for="setup-password" class="block text-xs font-semibold uppercase tracking-wider" style="color: var(--text-secondary);">
            Password or Passphrase
          </label>
          <span class="text-xs font-mono" style="color: var(--text-muted);">
            {charCount} chars
          </span>
        </div>

        <div class="password-wrapper">
          <input
            id="setup-password"
            type={showPassword ? 'text' : 'password'}
            bind:value={password}
            required
            minlength="8"
            maxlength="512"
            autocomplete="new-password"
            placeholder="8+ chars required • 15+ char passphrase recommended"
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

        <!-- NIST SP 800-63B-4 Password Guidance Meter -->
        <div class="mt-2.5 space-y-2">
          <div class="h-1.5 w-full rounded-full overflow-hidden" style="background: rgba(255, 255, 255, 0.07);">
            <div
              class="h-full transition-all duration-200 rounded-full"
              style="width: {charCount === 0 ? 0 : charCount < 8 ? Math.min(30, (charCount / 8) * 30) : charCount < 15 ? 60 : charCount < 64 ? 88 : 100}%;
                     background-color: {strengthTier === 'invalid' ? 'var(--color-danger)' : strengthTier === 'minimum' ? '#eab308' : 'var(--color-primary)'};"
            ></div>
          </div>

          <div class="flex items-center justify-between text-xs">
            <span
              class="font-medium"
              style="color: {strengthTier === 'invalid' ? '#fca5a5' : strengthTier === 'minimum' ? '#fde047' : strengthTier === 'empty' ? 'var(--text-muted)' : 'var(--color-primary)'};"
            >
              {strengthLabel}
            </span>
            {#if meetsRecommended}
              <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                    style="background: rgba(20, 184, 166, 0.15); color: var(--color-primary);">
                {isPassphraseTier ? '64+ Passphrase' : '15+ Recommended'}
              </span>
            {/if}
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1 text-[11px]" style="color: var(--text-muted);">
            <div class="flex items-center gap-1.5">
              <span style="color: {meetsMinimum ? 'var(--color-primary)' : 'var(--text-muted)'};">
                {meetsMinimum ? '✓' : '○'}
              </span>
              <span>8+ characters minimum</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span style="color: {meetsRecommended ? 'var(--color-primary)' : 'var(--text-muted)'};">
                {meetsRecommended ? '✓' : '○'}
              </span>
              <span>15+ characters recommended</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span style="color: var(--color-primary);">✓</span>
              <span>64+ char passphrases &amp; spaces allowed</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span style="color: var(--color-primary);">✓</span>
              <span>Unicode NFKC &amp; zero composition rules</span>
            </div>
          </div>
        </div>
      </div>

      <div>
        <label for="setup-confirm-password" class="block text-xs font-semibold uppercase tracking-wider mb-2" style="color: var(--text-secondary);">
          Confirm Password or Passphrase
        </label>
        <input
          id="setup-confirm-password"
          type={showPassword ? 'text' : 'password'}
          bind:value={confirmPassword}
          required
          minlength="8"
          maxlength="512"
          autocomplete="new-password"
          placeholder="Re-enter your password or passphrase"
          class="input-field"
        />
        {#if confirmPassword.length > 0 && !passwordsMatch}
          <p class="text-xs mt-1.5" style="color: #fca5a5;">
            Passwords do not match.
          </p>
        {/if}
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        class="w-full py-3 px-4 rounded-xl font-bold text-sm transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
        style="background-color: var(--color-primary); color: #020617;"
      >
        {submitting ? 'Initializing Administrator Account…' : 'Complete First-Boot Setup'}
      </button>
    </form>
  </div>
</div>
