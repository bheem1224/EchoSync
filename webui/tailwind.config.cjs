/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{html,js,svelte,ts}'
  ],
  safelist: ['bg-transparent', 'text-white'],
  theme: {
    extend: {
      colors: {
        // Design Token API Mappings
        canvas: 'var(--bg-canvas)',
        surface: 'var(--bg-surface)',
        'surface-elevated': 'var(--bg-surface-elevated)',
        'text-primary': 'var(--text-primary)',
        'text-muted': 'var(--text-muted)',
        primary: 'var(--color-primary)',
        danger: 'var(--color-danger)',
        
        // Legacy Mappings & Utilities
        'surface-hover': 'var(--bg-surface-elevated)',
        'primary-hover': 'var(--color-primary-hover)',
        'glass-border': 'var(--border-subtle)',
        glass: 'var(--glass)',
        error: 'var(--color-danger)',
        
        // Tailwind class fallbacks
        background: 'var(--bg-canvas)',
        input: 'var(--bg-input)',
        secondary: 'var(--text-muted)'
      },
      borderRadius: {
        // This maps 'rounded-global' to your 12px radius
        global: 'var(--radius)'
      }
    }
  },
  plugins: []
};