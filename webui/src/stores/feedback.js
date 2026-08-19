import { writable } from 'svelte/store';

function createFeedback() {
  const { subscribe, update, set } = writable({ toasts: [], loading: false });

  function addToast(message, type = 'success', duration = 3500) {
    if (typeof message === 'object' && message !== null) {
      type = message.type || type || 'success';
      duration = message.duration || duration || 3500;
      message = message.message || '';
    }
    const id = Date.now().toString() + Math.random().toString(36).substr(2, 4);
    update((s) => ({ ...s, toasts: [...s.toasts, { id, message, type }] }));
    setTimeout(() => removeToast(id), duration);
    return id;
  }

  function removeToast(id) {
    update((s) => ({ ...s, toasts: s.toasts.filter((t) => t.id !== id) }));
  }

  function setLoading(val) {
    update((s) => ({ ...s, loading: val }));
  }

  return { subscribe, addToast, removeToast, setLoading };
}

export const feedback = createFeedback();
