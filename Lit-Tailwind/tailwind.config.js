module.exports = {
  content: [
    './src/**/*.js',
    './src/**/*.ts',
    './src/**/*.html',
  ],
  plugins: [
    require('daisyui')
  ],
  daisyui: {
    styled: false,
    themes: false,
    base: false,
    utils: false,
    logs: true,
    rtl: false,
    prefix: "",
  },
  theme: {
    borderRadius: {
      DEFAULT: "10px",
    }
  }
};
