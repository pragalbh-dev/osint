/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // status visual-language tokens (defined in src/styles/tokens.css)
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        'surface-raised': 'var(--surface-raised)',
        hairline: 'var(--hairline)',
        'hairline-strong': 'var(--hairline-strong)',
        text: 'var(--text)',
        'text-dim': 'var(--text-dim)',
        'text-faint': 'var(--text-faint)',
        live: 'var(--live)',
        history: 'var(--history)',
        problem: 'var(--problem)',
        // interactive / selected — NEVER status
        accent: 'var(--accent-primary)',
        // alert-triage severity ramp — ONLY on alert-disposition cards, always text-labelled
        'sev-high': 'var(--sev-high)',
        'sev-watch': 'var(--sev-watch)',
        'sev-clear': 'var(--sev-clear)',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SF Mono', 'Menlo', 'Consolas', 'monospace'],
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        node: 'var(--radius-node)',
        chip: 'var(--radius-chip)',
      },
    },
  },
  plugins: [],
}
