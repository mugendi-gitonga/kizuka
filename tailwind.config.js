/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./landing/templates/**/*.{html,js}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          dark: '#0f172e',
          navy: '#1a2847',
          secondary: '#2d3f6e',
        },
        accent: {
          blue: '#00d4ff',
          neon: '#0096ff',
          purple: '#7c3aed',
          pink: '#ff006e',
        },
        text: {
          light: '#ffffff',
          secondary: '#b0b8d4',
          tertiary: '#8892b0',
        },
        bg: {
          dark: '#0a0f23',
        },
      },
      fontFamily: {
        'space': ['Space Grotesk', 'sans-serif'],
        'inter': ['Inter', 'sans-serif'],
      },
      animation: {
        'glow': 'glow 3s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%, 100%': {
            boxShadow: '0 0 50px rgba(0, 212, 255, 0.2), inset 0 0 50px rgba(0, 212, 255, 0.05)',
          },
          '50%': {
            boxShadow: '0 0 80px rgba(0, 212, 255, 0.4), inset 0 0 50px rgba(0, 212, 255, 0.1)',
          },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
      },
    },
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        kizuka: {
          "primary": "#00d4ff",
          "primary-focus": "#0096ff",
          "primary-content": "#0f172e",
          "secondary": "#7c3aed",
          "secondary-focus": "#6d28d9",
          "secondary-content": "#ffffff",
          "accent": "#ff006e",
          "accent-focus": "#e0005e",
          "accent-content": "#ffffff",
          "neutral": "#2d3f6e",
          "neutral-focus": "#1a2847",
          "neutral-content": "#ffffff",
          "base-100": "#0a0f23",
          "base-200": "#0f172e",
          "base-300": "#1a2847",
          "base-content": "#ffffff",
          "info": "#0096ff",
          "success": "#10b981",
          "warning": "#f59e0b",
          "error": "#ef4444",
        },
      },
    ],
  },
}
