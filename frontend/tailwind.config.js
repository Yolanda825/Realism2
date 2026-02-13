/** Tailwind CSS configuration for premium frontend */
module.exports = {
  content: ["./index.html","./src/**/*.{js,jsx,ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f5fbff',
          100: '#e6f1ff',
          200: '#b3d8ff',
          500: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
}
