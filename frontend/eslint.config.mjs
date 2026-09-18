import nextConfig from "eslint-config-next";

const eslintConfig = [
  {
    ignores: [".next/**", "node_modules/**", "playwright-report/**", "test-results/**"],
  },
  ...nextConfig,
];

export default eslintConfig;
