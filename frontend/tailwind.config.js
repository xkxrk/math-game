/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        dlt: {
          red: '#ef4444',
          blue: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
}
