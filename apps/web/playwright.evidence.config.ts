import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './evidence',
  use: { baseURL: 'http://localhost:8090', channel: 'chrome' },
  workers: 1,
})
