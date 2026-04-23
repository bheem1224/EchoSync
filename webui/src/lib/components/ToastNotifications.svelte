<script>
  import { onMount, onDestroy } from 'svelte';

  let toasts = [];

  function handleToastEvent(event) {
    if (!event.detail || !event.detail.message) return;

    const toast = {
      id: Date.now() + Math.random().toString(36).substr(2, 9),
      message: event.detail.message,
      type: event.detail.type || 'info'
    };

    toasts = [...toasts, toast];

    setTimeout(() => {
      toasts = toasts.filter(t => t.id !== toast.id);
    }, 4000);
  }

  onMount(() => {
    window.addEventListener('es-toast', handleToastEvent);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('es-toast', handleToastEvent);
    }
  });

  function getBorderColorClass(type) {
    switch (type) {
      case 'success': return 'border-l-accent';
      case 'error': return 'border-l-error-border';
      case 'warning': return 'border-l-warning-border';
      default: return 'border-l-primary';
    }
  }

  function getIcon(type) {
    switch (type) {
      case 'success': return '✓';
      case 'error': return '✕';
      case 'warning': return '⚠';
      default: return 'ℹ';
    }
  }

  function getIconColorClass(type) {
    switch (type) {
      case 'success': return 'text-accent';
      case 'error': return 'text-error-text';
      case 'warning': return 'text-warning-text';
      default: return 'text-primary';
    }
  }
</script>

<div class="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
  {#each toasts as toast (toast.id)}
    <div class="pointer-events-auto flex items-center gap-3 p-4 bg-surface backdrop-blur-md border border-glass-border {getBorderColorClass(toast.type)} border-l-4 shadow-xl rounded-global animate-slide-up">
      <span class="font-bold {getIconColorClass(toast.type)}">{getIcon(toast.type)}</span>
      <span class="text-sm font-medium text-primary">{toast.message}</span>
    </div>
  {/each}
</div>

<style>
  .animate-slide-up {
    animation: slideUp 0.3s ease-out forwards;
  }
  @keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
</style>
