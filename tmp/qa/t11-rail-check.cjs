// T11 QA driver — verifies the rail's Watching row in LIVE mode, cold boot and after a tripwire
// fires. Deliberately NOT a project dependency (playwright is not in frontend/package.json — this is
// QA tooling, not app code). To run:
//
//   cd frontend && npm i --no-save playwright && cd ..
//   CHANAKYA_ROOT=$PWD backend/.venv/bin/uvicorn chanakya.api.app:create_app --factory --port 8041 &
//   NODE_PATH=frontend/node_modules node tmp/qa/t11-rail-check.cjs
//
// CHROME points at an already-downloaded browser so `npx playwright install` isn't needed; override
// it (or the T11_BASE origin) for another box.
const { chromium } = require('playwright')
const CHROME = '/home/synaptic/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = process.env.T11_BASE || 'http://127.0.0.1:8041'
const OUT = __dirname

const railText = (p) => p.evaluate(() => document.querySelector('aside')?.innerText)
const watchRow = async (p) => {
  const t = await railText(p)
  const i = t.indexOf('Watching')
  return t.slice(i, t.indexOf('\n', t.indexOf('indicators & warning', i)))
}

;(async () => {
  const b = await chromium.launch({ executablePath: CHROME })
  const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
  const errors = []
  p.on('console', (m) => m.type() === 'error' && errors.push(m.text()))

  await p.goto(`${BASE}/?mode=live`, { waitUntil: 'networkidle' })
  await p.waitForTimeout(2500)
  console.log('COLD BOOT  :', JSON.stringify(await watchRow(p)))
  await p.locator('aside').first().screenshot({ path: `${OUT}/t11-rail-cold-boot.png` })
  await p.screenshot({ path: `${OUT}/t11-app-cold-boot.png` })

  // Ingest the two withheld Rahwali documents — the relocation tripwire should fire.
  for (const doc of ['d18_rahwali_pass1', 'd19_rahwali_confirm']) {
    const row = p
      .locator('aside')
      .first()
      .locator('div')
      .filter({ hasText: doc })
      .filter({ has: p.locator('button') })
      .last()
    await row.locator('button').first().click()
    await p.waitForTimeout(4000)
  }
  await p.waitForTimeout(3000)
  console.log('AFTER FIRE :', JSON.stringify(await watchRow(p)))
  await p.locator('aside').first().screenshot({ path: `${OUT}/t11-rail-fired.png` })
  await p.screenshot({ path: `${OUT}/t11-app-fired.png` })

  console.log('CONSOLE ERRORS:', JSON.stringify(errors.slice(0, 5)))
  await b.close()
})().catch((e) => {
  console.error(e)
  process.exit(1)
})
