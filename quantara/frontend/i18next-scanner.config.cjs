module.exports = {
  input: ['src/**/*.{js,jsx,ts,tsx}'],
  output: './public/locales/{{lng}}/{{ns}}.json',
  options: {
    lngs: ['en', 'es'],
    ns: ['common'],
    defaultLng: 'en',
    defaultNs: 'common',
    keySeparator: false,
    interpolation: { prefix: '{{', suffix: '}}' },
    removeUnusedKeys: true,
  },
};
