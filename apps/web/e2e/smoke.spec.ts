import { test, expect } from '@playwright/test'
test('login, dashboard, occurrence list and map', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('DADOS SINTÉTICOS / DEMONSTRAÇÃO')).toBeVisible()
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await page.getByRole('button', { name: /Ocorrências/ }).click()
  await page.getByLabel('Buscar ocorrências').fill('DEMO-2026-0001')
  await expect(page.getByText('DEMO-2026-0001')).toBeVisible()
  await page.getByRole('button', { name: /Mapa & Hotspots/ }).click()
  await expect(page.getByRole('img', { name: /Mapa de ocorrências/ })).toBeVisible()
  await page.getByRole('button', { name: /Croqui \/ Rotas/ }).click()
  await expect(page.getByRole('img', { name: /Trajeto das visitas/ })).toBeVisible()
})
test('mobile navigation remains usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await page.getByRole('button', { name: /Chatbot/ }).click()
  await expect(page.getByRole('heading', { name: 'Assistente informacional' })).toBeVisible()
})
test('all primary pages open with authenticated data', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Entrar' }).click()
  for (const name of ['Dashboard', 'Ocorrências', 'Mapa & Hotspots', 'Croqui / Rotas', 'Chatbot', 'OCR / Document AI', 'Repositório', 'Qualidade de Dados', 'Analytics / IA', 'Relatórios', 'Administração', 'Auditoria']) {
    await page.getByRole('navigation', { name: 'Navegação principal' }).getByRole('button', { name: new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).click()
    await expect(page.getByRole('heading', { name, exact: true, level: 1 })).toBeVisible()
  }
})

