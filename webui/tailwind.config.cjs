/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{html,js,svelte,ts}'
  ],
  safelist: ['bg-transparent', 'text-white'],
  theme: {
    extend: {
      colors: {
        // This maps 'bg-background' to your very dark void color
        background: 'var(--bg-main)',

        // This maps 'bg-surface' to your card background color
        surface: 'var(--bg-card)',

        // This maps 'bg-surface-hover' to the hover surface tone
        'surface-hover': 'var(--surface-hover)',

        // This maps 'bg-input' to input/field backgrounds
        input: 'var(--bg-input)',

        // This maps 'text-primary' or 'bg-primary' to your Teal brand color
        primary: 'var(--color-primary)',
        'primary-hover': 'var(--color-primary-hover)',

        // This maps 'text-secondary' to your muted slate color
        secondary: 'var(--text-muted)',

        // This maps 'border-glass-border' to your subtle white borders
        'glass-border': 'var(--border-subtle)',

        // Supports glass-style surfaces where needed
        glass: 'var(--glass)',

        error: 'var(--error)'
      },
      borderRadius: {
        // This maps 'rounded-global' to your 12px radius
        global: 'var(--radius)'
      }
    }
  },
  plugins: []
};