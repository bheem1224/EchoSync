module.exports = {
  content: [
    './src/**/*.{html,js,svelte,ts}'
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: 'var(--es-bg-base)'
        },
        surface: {
          DEFAULT: 'var(--es-bg-surface)',
          hover: 'var(--es-bg-surface-hover)'
        },
        primary: {
          DEFAULT: 'var(--es-text-primary)'
        },
        secondary: {
          DEFAULT: 'var(--es-text-secondary)'
        },
        accent: {
          DEFAULT: 'var(--es-accent)'
        },
        border: {
          DEFAULT: 'var(--es-border-color)'
        },
        error: {
          bg: 'var(--es-error-bg)',
          text: 'var(--es-error-text)',
          border: 'var(--es-error-border)'
        },
        warning: {
          bg: 'var(--es-warning-bg)',
          text: 'var(--es-warning-text)',
          border: 'var(--es-warning-border)'
        },
        success: {
          bg: 'var(--es-success-bg)',
          text: 'var(--es-success-text)'
        }
      },
      borderRadius: {
        global: 'var(--es-border-radius)'
      }
    }
  },
  plugins: []
}
