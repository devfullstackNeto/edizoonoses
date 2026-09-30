import { test, expect, type Browser, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { createHash } from 'node:crypto'

test.use({ viewport: { width: 1440, height: 900 }, video: 'off' })

const root = path.resolve(process.cwd(), '../../docs/evidence')
const desktop = path.join(root, 'screenshots/desktop')
const mobileDir = path.join(root, 'screenshots/mobile')
const videos = path.join(root, 'videos')
const reports = path.join(root, 'reports')
for (const folder of [desktop, mobileDir, videos, reports]) fs.mkdirSync(folder, { recursive: true })

const captured: { id: string; file: string; description: string }[] = []
async function shot(page: Page, folder: string, name: string, description: string) {
  const target = path.join(folder, name)
  await page.evaluate(() => window.scrollTo(0, 0))
  const viewportOnly = /^(17|18|19|20|21|26)_/.test(name)
  await page.screenshot({ path: target, fullPage: !viewportOnly, animations: 'disabled', timeout: 15000 })
  captured.push({ id: name.slice(0, 2), file: path.relative(root, target).replaceAll('\\', '/'), description })
}
async function nav(page: Page, name: RegExp) {
  await page.getByRole('navigation', { name: 'Navegação principal' }).getByRole('button', { name }).click()
}
async function mobileField(page: Page, routeName: string, status: string) {
  await page.reload()
  await nav(page, /Modo Campo/)
  await page.getByLabel('Selecionar rota de campo').selectOption({ label: `${routeName} · ${status}` })
  await expect(page.getByRole('heading', { name: /Visita DEMO-/ })).toBeVisible()
}
async function waitJob(page: Page, id: string) {
  const token = await page.evaluate(() => sessionStorage.getItem('edi_token'))
  await expect.poll(async () => {
    const response = await page.request.get(`http://localhost:8090/api/v1/ocr/jobs/${id}`, { headers: { Authorization: `Bearer ${token}` } })
    return (await response.json()).status as string
  }, { timeout: 90000 }).toBe('needs_review')
}
function digest(file: string) { return createHash('sha256').update(fs.readFileSync(file)).digest('hex') }

test('captura reproduzível da versão final DEMO', async ({ page, browser }: { page: Page; browser: Browser }) => {
  test.setTimeout(150000)
  const stamp = Date.now()
  const description = `Evidência final sintética ${stamp}`
  const routeName = `Rota Evidência DEMO ${stamp}`
  let mobile: Page | undefined
  let mobileContext: Awaited<ReturnType<Browser['newContext']>> | undefined
  try {
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()
    await shot(page, desktop, '01_login.png', 'Login com aviso de dados sintéticos')
    await page.getByRole('button', { name: 'Entrar' }).click()
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await shot(page, desktop, '02_dashboard.png', 'Dashboard antes da jornada')

    await nav(page, /Ocorrências/)
    await page.getByRole('button', { name: /Nova ocorrência/ }).click()
    const form = page.getByRole('dialog', { name: 'Formulário de ocorrência' })
    await form.getByLabel('Descrição').fill(description)
    await form.getByLabel('Endereço').fill('Rua Sintética 1')
    await form.getByRole('button', { name: 'Buscar endereço' }).click()
    await expect(form.locator('.field-visit').first()).toBeVisible()
    await form.locator('.field-visit').first().click()
    const createResponse = page.waitForResponse(r => r.url().endsWith('/api/v1/occurrences') && r.request().method() === 'POST')
    await form.getByRole('button', { name: 'Salvar' }).click()
    const created = await (await createResponse).json() as { id: string; protocol: string }
    const protocol = created.protocol

    await nav(page, /Mapa & Hotspots/)
    await expect(page.getByRole('img', { name: /Mapa de ocorrências/ })).toBeVisible()
    await shot(page, desktop, '03_mapa_gis.png', 'Mapa GIS com pontos sintéticos e territórios')
    await page.getByLabel('Buscar endereço no mapa').fill('Rua Sintética 1')
    await page.getByRole('button', { name: 'Buscar', exact: true }).click()
    await expect(page.locator('.map-suggestion').first()).toBeVisible()
    await shot(page, desktop, '04_busca_endereco.png', 'Sugestões reais da busca na seed')
    await page.locator('.map-suggestion').first().click()
    await page.locator('#pilot-map').click({ position: { x: 100, y: 120 } })
    await expect(page.getByText('Ponto selecionado manualmente', { exact: true }).first()).toBeVisible()
    await shot(page, desktop, '05_correcao_manual_ponto.png', 'Correção manual do marcador no Leaflet')
    await page.getByLabel('Ocorrência do ponto pesquisado').selectOption({ label: protocol })
    const locationResponse = page.waitForResponse(r => r.url().endsWith(`/api/v1/occurrences/${created.id}/location`) && r.request().method() === 'PATCH')
    await page.getByRole('button', { name: 'Salvar ponto na ocorrência' }).click()
    const location = await (await locationResponse).json() as { latitude: number; longitude: number }
    const detail = page.getByRole('dialog', { name: 'Detalhe da ocorrência' })
    await expect(detail.getByRole('heading', { name: protocol })).toBeVisible()
    await shot(page, desktop, '06_detalhe_ocorrencia.png', 'Ocorrência DEMO com ponto georreferenciado')
    await detail.getByRole('button', { name: 'Fechar' }).click()

    await nav(page, /Croqui \/ Rotas/)
    await page.getByLabel('Buscar ponto da rota').fill(protocol)
    await page.locator('#route-points .check-row').filter({ hasText: protocol }).locator('input').check()
    await page.getByLabel('Nome do plano').fill(routeName)
    await page.getByLabel('Latitude de partida').fill(String(location.latitude + 0.005))
    await page.getByLabel('Longitude de partida').fill(String(location.longitude + 0.005))
    await shot(page, desktop, '07_criacao_rota.png', 'Seleção de ocorrência e ponto de partida')
    await page.getByRole('button', { name: 'Gerar e salvar rota' }).click()
    await expect(page.getByText('Rota salva com sucesso.')).toBeVisible()
    await expect(page.getByRole('img', { name: 'Trajeto das visitas' })).toBeVisible()
    await shot(page, desktop, '08_rota_desenhada.png', 'Trajeto salvo, marcador de partida e fallback local')

    mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, hasTouch: true })
    mobile = await mobileContext.newPage()
    await mobile.goto('/')
    await mobile.getByRole('button', { name: 'Entrar' }).click()
    await nav(mobile, /Mapa & Hotspots/)
    await expect(mobile.getByRole('img', { name: /Mapa de ocorrências/ })).toBeVisible()
    await shot(mobile, mobileDir, '01_mapa_mobile.png', 'Mapa em viewport 390×844')
    await nav(mobile, /Modo Campo/)
    await mobile.getByLabel('Selecionar rota de campo').selectOption({ label: `${routeName} · planned` })
    await shot(mobile, mobileDir, '02_modo_campo_mobile.png', 'Rota planejada no Modo Campo responsivo')

    await nav(page, /Modo Campo/)
    await page.getByLabel('Selecionar rota de campo').selectOption({ label: `${routeName} · planned` })
    await shot(page, desktop, '09_modo_campo.png', 'Modo Campo com rota planejada')
    await page.getByRole('button', { name: 'Iniciar rota' }).click()
    await expect(page.getByText('Rota iniciada.')).toBeVisible()
    await mobileField(mobile, routeName, 'active')
    await shot(mobile, mobileDir, '03_proximo_destino_mobile.png', 'Próximo destino e endereço da rota ativa')

    const far = { latitude: location.latitude + 0.02, longitude: location.longitude, accuracy: 15 }
    await page.context().grantPermissions(['geolocation'])
    await page.context().setGeolocation(far)
    await page.getByRole('button', { name: 'Obter localização' }).click()
    await expect(page.getByLabel('Latitude do check-in')).not.toHaveValue('')
    await page.getByRole('button', { name: 'Registrar check-in agora' }).click()
    await expect(page.getByText('Check-in registrado.')).toBeVisible()
    await shot(page, desktop, '10_checkin.png', 'Check-in explícito durante rota ativa')
    await mobile.context().grantPermissions(['geolocation'])
    await mobile.context().setGeolocation(far)
    await mobile.getByRole('button', { name: 'Obter localização' }).click()
    await expect(mobile.getByLabel('Latitude do check-in')).not.toHaveValue('')
    await mobile.getByRole('button', { name: 'Registrar check-in agora' }).click()
    await expect(mobile.getByText('Check-in registrado.')).toBeVisible()
    await shot(mobile, mobileDir, '04_checkin_mobile.png', 'Geolocation API e check-in no viewport móvel')

    await page.getByRole('button', { name: 'Confirmar chegada' }).click()
    await expect(page.getByText(/Fora do raio/)).toBeVisible()
    await shot(page, desktop, '11_geofence_fora_raio.png', 'Geofence fora do raio esperado')
    await mobileField(mobile, routeName, 'active')
    await mobile.getByLabel('Latitude de chegada').fill(String(far.latitude))
    await mobile.getByLabel('Longitude de chegada').fill(String(far.longitude))
    await mobile.getByRole('button', { name: 'Confirmar chegada' }).click()
    await expect(mobile.getByText(/Fora do raio/)).toBeVisible()
    await shot(mobile, mobileDir, '05_geofence_mobile.png', 'Aviso de geofence fora do raio no celular')
    await page.getByLabel('Confirmação manual fora do raio').check()
    await page.getByLabel('Justificativa').fill('Ponto de entrada confirmado manualmente em DEMO')
    await page.getByRole('button', { name: 'Confirmar chegada' }).click()
    await expect(page.getByRole('button', { name: 'Iniciar visita' })).toBeVisible()
    await shot(page, desktop, '12_chegada_override.png', 'Chegada confirmada com override justificado')
    await page.getByRole('button', { name: 'Iniciar visita' }).click()
    await expect(page.getByRole('heading', { name: 'Evidência' })).toBeVisible()
    await shot(page, desktop, '13_visita_andamento.png', 'Visita iniciada com horário persistido')
    await mobileField(mobile, routeName, 'active')
    await shot(mobile, mobileDir, '06_visita_mobile.png', 'Visita em andamento no celular')
    await page.getByLabel('Resultado').selectOption('requer revisita')
    await page.getByLabel('Observação', { exact: true }).fill('Observação sintética para relatório de evidências')
    await shot(page, desktop, '14_resultado_visita.png', 'Resultado e observação preparados na visita')
    await page.getByLabel('Descrição').fill('Pendência sintética de vistoria')
    await page.getByLabel('Severidade').selectOption('Alta')
    await page.getByRole('button', { name: 'Registrar pendência' }).click()
    await expect(page.getByText('Pendência registrada.')).toBeVisible()
    await shot(page, desktop, '15_pendencia.png', 'Pendência criada e vinculada à visita')
    await mobileField(mobile, routeName, 'active')
    await shot(mobile, mobileDir, '08_pendencia_mobile.png', 'Pendência visível na visita móvel')

    const fixture = path.resolve(process.cwd(), '../api/fixtures/relatorio_visita_sintetico.png')
    await page.getByLabel('Fotografar ou selecionar arquivo').setInputFiles(fixture)
    await expect(page.getByRole('img', { name: 'Prévia da evidência' })).toBeVisible()
    await shot(page, desktop, '16_captura_evidencia.png', 'Prévia real do arquivo selecionado antes do envio')
    await mobile.getByLabel('Fotografar ou selecionar arquivo').setInputFiles(fixture)
    await expect(mobile.getByRole('img', { name: 'Prévia da evidência' })).toBeVisible()
    await shot(mobile, mobileDir, '07_captura_foto_mobile.png', 'Seleção de foto e prévia no celular')
    const jobResponse = page.waitForResponse(r => r.url().endsWith('/api/v1/ocr/jobs') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Confirmar envio' }).click()
    const job = await (await jobResponse).json() as { id: string }
    await expect(page.getByText('Evidência enviada e OCR solicitado.')).toBeVisible()
    await page.getByRole('button', { name: /Revisar OCR/ }).click()
    await expect(page.locator('.ocr-review img')).toBeVisible()
    await shot(page, desktop, '17_documento_original.png', 'Documento original servido pelo MinIO na revisão')
    await waitJob(page, job.id)
    await expect(page.getByRole('button', { name: 'Aprovar campos' })).toBeVisible({ timeout: 15000 })
    await shot(page, desktop, '18_ocr_executado.png', 'Tesseract real com texto, confiança e campos')

    await page.getByLabel('Documento existente').selectOption({ label: 'dossie_visita_sintetico.pdf' })
    const pdfResponse = page.waitForResponse(r => r.url().endsWith('/api/v1/ocr/jobs') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Processar existente' }).click()
    const pdfJob = await (await pdfResponse).json() as { id: string }
    await waitJob(page, pdfJob.id)
    await page.locator('.ocr-layout .field-visit').filter({ hasText: 'dossie_visita_sintetico.pdf' }).first().click()
    await expect(page.locator('.ocr-review select').first()).toBeVisible()
    await page.locator('.ocr-review select').first().selectOption('2')
    await page.locator('.ocr-review details summary').first().click()
    await shot(page, desktop, '19_ocr_multipagina.png', 'PDF real de duas páginas, com resultado da página 2')
    await page.locator('.ocr-review details summary').first().click()
    await page.locator('.ocr-layout .field-visit').filter({ hasText: 'relatorio_visita_sintetico.png' }).first().click()
    await expect(page.getByRole('button', { name: 'Aprovar campos' })).toBeVisible()
    const detected = page.locator('.ocr-field input')
    if (await detected.count()) await detected.first().fill('Valor sintético corrigido na revisão')
    await page.getByLabel('Novo campo').fill('revisao_demo')
    await page.getByLabel('Valor').fill('confirmado')
    await page.getByRole('button', { name: 'Adicionar campo' }).click()
    await shot(page, desktop, '20_revisao_humana.png', 'Correção e adição de campos antes da aprovação')
    await page.getByRole('button', { name: 'Aprovar campos' }).click()
    await expect(page.getByText('Revisão aprovada.')).toBeVisible()
    await shot(page, desktop, '21_documento_aprovado.png', 'OCR aprovado com campos revisados')

    await nav(page, /Repositório/)
    await page.getByLabel('Buscar documento').fill('relatorio_visita_sintetico.png')
    await expect(page.locator('.document').first()).toBeVisible()
    await shot(page, desktop, '22_repositorio_eletronico.png', 'Documento armazenado e pesquisável no repositório')
    await nav(page, /Chatbot/)
    await page.getByLabel('Pergunta').fill('morcegos')
    await page.getByRole('button', { name: 'Enviar' }).click()
    await expect(page.getByText(/Fonte:/).first()).toBeVisible()
    await shot(page, desktop, '23_chatbot.png', 'Resposta do chatbot com fonte')
    await nav(page, /Qualidade de Dados/)
    await expect(page.getByRole('heading', { name: 'Qualidade de Dados' })).toBeVisible()
    await shot(page, desktop, '24_qualidade_dados.png', 'Tela de regras e achados de qualidade')
    await nav(page, /Auditoria/)
    await expect(page.getByRole('heading', { name: 'Eventos de auditoria' })).toBeVisible()
    await shot(page, desktop, '25_auditoria.png', 'Auditoria após a execução da jornada')

    await nav(page, /Modo Campo/)
    await page.getByLabel('Selecionar rota de campo').selectOption({ label: `${routeName} · active` })
    await page.getByLabel('Resultado').selectOption('requer revisita')
    await page.getByLabel('Observação', { exact: true }).fill('Conclusão sintética da visita de evidência')
    await page.getByRole('button', { name: 'Concluir visita' }).click()
    await expect(page.getByText('Visita concluída.')).toBeVisible()
    await mobileField(mobile, routeName, 'active')
    await shot(mobile, mobileDir, '09_conclusao_mobile.png', 'Visita concluída no fluxo móvel')
    await page.getByRole('button', { name: 'Encerrar rota' }).click()
    await expect(page.getByText('Rota encerrada.')).toBeVisible()
    await nav(page, /Ocorrências/)
    await expect(detail.getByRole('heading', { name: protocol })).toBeVisible()
    await detail.locator('.dialog').evaluate(el => { el.scrollTop = el.scrollHeight })
    await shot(page, desktop, '26_timeline_ocorrencia.png', 'Timeline operacional completa da ocorrência')
    await detail.getByRole('button', { name: 'Fechar' }).click()
    await nav(page, /Dashboard/)
    await expect(page.getByText('Operação de campo')).toBeVisible()
    await shot(page, desktop, '27_dashboard_apos_operacoes.png', 'Indicadores de campo após visita e OCR')

    fs.writeFileSync(path.join(reports, 'capture-manifest.json'), JSON.stringify({
      captured_at: new Date().toISOString(),
      protocol, occurrence_id: created.id, route_name: routeName,
      screenshots: captured.map(item => ({ ...item, sha256: digest(path.join(root, item.file)) })),
    }, null, 2))
  } finally {
    if (mobileContext) await mobileContext.close()
    await page.close()
  }
})
