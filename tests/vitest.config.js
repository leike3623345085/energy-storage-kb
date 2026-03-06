import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'mocks/',
        '*.config.js',
        '**/*.test.js'
      ]
    },
    include: ['**/*.test.js'],
    exclude: ['node_modules/', 'coverage/']
  }
});
