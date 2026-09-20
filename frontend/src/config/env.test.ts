/**
 * Phase 6.15.8 — Frontend environment configuration invariants.
 *
 * Guards the deployment configuration contract from inside the normal test
 * suite (in addition to scripts/verify_frontend_build_security.mjs, which
 * scans the BUILT bundle):
 *
 *   1. `frontend/src` only ever reads the single public Vite variable
 *      VITE_API_BASE_URL — no backend secret is `VITE_`-prefixed, so no
 *      backend secret can reach the browser bundle by construction.
 *   2. The API boundary default is the same-origin `/api` path (never a
 *      localhost address), so a production build cannot accidentally point
 *      at a development backend.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Vitest runs from the frontend/ directory; jsdom rewrites import.meta.url
// to an http:// URL, so the real filesystem path must come from cwd.
const SRC_ROOT = join(process.cwd(), 'src')

const ALLOWED_ENV_VARS = new Set(['VITE_API_BASE_URL'])

function collectSourceFiles(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...collectSourceFiles(full))
    else if (/\.(ts|tsx|js|jsx)$/.test(entry)) out.push(full)
  }
  return out
}

describe('frontend environment configuration', () => {
  it('reads only the public VITE_API_BASE_URL variable anywhere in src/', () => {
    const usage = /import\.meta\.env\??\.([A-Za-z0-9_]+)/g
    const offenders: string[] = []
    for (const file of collectSourceFiles(SRC_ROOT)) {
      const content = readFileSync(file, 'utf8')
      for (const match of content.matchAll(usage)) {
        if (!ALLOWED_ENV_VARS.has(match[1])) offenders.push(`${file} -> ${match[1]}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('uses no secret-shaped VITE_ variable name anywhere in src/', () => {
    const forbidden = /VITE_[A-Z_]*(SECRET|SERVICE_ROLE|PASSWORD|TOKEN|API_KEY|DATABASE)/
    const offenders: string[] = []
    for (const file of collectSourceFiles(SRC_ROOT)) {
      const content = readFileSync(file, 'utf8')
      const match = content.match(forbidden)
      if (match) offenders.push(`${file} -> ${match[0]}`)
    }
    expect(offenders).toEqual([])
  })

  it('keeps the API base URL default same-origin (/api), not localhost', () => {
    // The services resolve: (import.meta.env?.VITE_API_BASE_URL ?? '/api')
    // Verify the fallback literal is the same-origin path, not a host URL.
    const api = readFileSync(join(SRC_ROOT, 'services', 'api.ts'), 'utf8')
    expect(api).toMatch(/VITE_API_BASE_URL\s*\?\? *['"]\/api['"]/)
    expect(api).not.toMatch(/localhost|127\.0\.0\.1/)
  })
})
