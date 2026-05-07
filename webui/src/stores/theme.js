import { writable } from 'svelte/store';

function createThemeStore() {
  const { subscribe, set, update } = writable({
    current: 'default',
    themes: {
      default: {
        name: 'Default',
        variables: {} // Uses root variables from app.css
      }
    }
  });

  function setTheme(themeId) {
    update(s => {
      if (s.themes[themeId]) {
        localStorage.setItem('soulsync.theme', themeId);
        return { ...s, current: themeId };
      }
      return s;
    });
  }

  function registerTheme(themeId, themeData) {
    update(s => {
      const next = {
        ...s,
        themes: { ...s.themes, [themeId]: themeData }
      };
      
      // Inject CSS variables if provided
      if (themeData.css) {
        let el = document.getElementById(`theme-style-${themeId}`);
        if (!el) {
          el = document.createElement('style');
          el.id = `theme-style-${themeId}`;
          document.head.appendChild(el);
        }
        el.textContent = `.theme-${themeId} { ${themeData.css} }`;
      }
      
      return next;
    });
  }

  function init() {
    if (typeof localStorage !== 'undefined') {
      const saved = localStorage.getItem('soulsync.theme');
      if (saved) setTheme(saved);
    }
  }

  return { subscribe, setTheme, registerTheme, init };
}

export const theme = createThemeStore();
