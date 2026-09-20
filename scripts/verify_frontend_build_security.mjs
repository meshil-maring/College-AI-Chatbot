/**
 * Phase 6.15.8 — Frontend production build security verification.
 *
 * Run after `npm run build`:
 *
 *   node scripts/verify_frontend_build_security.mjs
 *
 * Fails (exit 1) when ANY of the following is true:
 *
 *   1. frontend/dist contains a secret-shaped string (OpenRouter key, the
 *      Supabase service-role/"secret" key reference, private-key PEM text,
 *      an R2 secret, a hardcoded password literal, ...).
 *   2. frontend/dist contains "localhost" / "127.0.0.1" — the production
 *      bundle must use the same-origin `/api` base URL, never a development
 *      backend address.
 *   3. frontend/src reads any Vite env variable other than the single
 *      public VITE_API_BASE_URL (only intentionally public configuration may
 *      reach the browser bundle).
 *   4. .env.example files contain real-looking credentials (placeholders
 *      only are allowed).
 *
 * This is a static scan, not a proof — it is a fast guard against the
 * realistic accident classes for this project.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'

const repoRoot = process.cwd()
const problems = []

// ---------------------------------------------------------------------------
// 1+2. Build artifact scan (frontend/dist)
// ---------------------------------------------------------------------------

const distDir = join(repoRoot, 'frontend', 'dist')
const SECRET_PATTERNS = [
  [/sk-or-/i, 'OpenRouter API key literal'],
  [/SUPABASE_SECRET/i, 'Supabase secret key reference'],
  [/SUPABASE_SERVICE_ROLE/i, 'Supabase service-role key reference'],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, 'Private key PEM block'],
  [/r2_secret/i, 'Cloudflare R2 secret reference'],
  [/OPENROUTER_API_KEY/, 'OpenRouter key variable reference'],
  [/DATABASE_URL/, 'Database connection string reference'],
  [/\bpassword\s*[:=]\s*["'][^"']{4,}["']/i, 'Hardcoded password literal'],
]
const LOCALHOST_PATTERN = /localhost|127\.0\.0\.1/

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...walk(full))
    else out.push(full)
  }
  return out
}

let distFiles = []
try {
  distFiles = walk(distDir)
} catch {
  problems.push('frontend/dist does not exist — run `npm run build` first.')
}

for (const file of distFiles) {
  if (!/\.(js|css|html|map|json|txt|svg)$/.test(file)) continue
  const content = readFileSync(file, 'utf8')
  for (const [pattern, label] of SECRET_PATTERNS) {
    if (pattern.test(content)) {
      problems.push(`dist secret pattern (${label}) found in ${relative(repoRoot, file)}`)
    }
  }
  if (LOCALHOST_PATTERN.test(content)) {
    problems.push(`dist contains a localhost/127.0.0.1 reference in ${relative(repoRoot, file)}`)
  }
}

// ---------------------------------------------------------------------------
// 3. Source env-variable allowlist (frontend/src)
// ---------------------------------------------------------------------------

const srcDir = join(repoRoot, 'frontend', 'src')
const ENV_USAGE = /import\.meta\.env\??\.([A-Za-z0-9_]+)/g
const ALLOWED_ENV_VARS = new Set(['VITE_API_BASE_URL'])

for (const file of walk(srcDir)) {
  if (!/\.(ts|tsx|js|jsx)$/.test(file)) continue
  const content = readFileSync(file, 'utf8')
  for (const match of content.matchAll(ENV_USAGE)) {
    const name = match[1]
    if (!ALLOWED_ENV_VARS.has(name)) {
      problems.push(
        `frontend/src reads non-allowlisted env var "${name}" in ${relative(repoRoot, file)}`,
      )
    }
  }
}

// ---------------------------------------------------------------------------
// 4. .env.example hygiene — placeholders only, never credentials
// ---------------------------------------------------------------------------

const ENV_EXAMPLES = [
  join(repoRoot, 'backend', '.env.example'),
  join(repoRoot, 'frontend', '.env.example'),
]
for (const file of ENV_EXAMPLES) {
  const content = readFileSync(file, 'utf8')
  // Only VALUE-shaped patterns apply here: a .env.example is SUPPOSED to
  // name its variables (e.g. OPENROUTER_API_KEY=) with placeholder values.
  const valuePatterns = [
    [/=\s*sk-or-/i, 'OpenRouter API key value'],
    [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, 'Private key PEM block'],
    [/=\s*[A-Za-z0-9_\-]{60,}/, 'Long random credential value'],
  ]
  for (const [pattern, label] of valuePatterns) {
    if (pattern.test(content)) {
      problems.push(`${relative(repoRoot, file)} contains a secret-shaped value (${label})`)
    }
  }
  // Real-looking long random assignments (not <your-...> placeholders).
  const assignments = content.matchAll(/^[A-Z_]+=(\S+)$/gm)
  for (const m of assignments) {
    const value = m[1]
    if (value.startsWith('<') || value === '' ) continue
    if (value.length >= 40 && /^[A-Za-z0-9_\-]+=*$/.test(value)) {
      problems.push(`${relative(repoRoot, file)} line value looks like a real credential (withheld)`)
    }
  }
}

// ---------------------------------------------------------------------------

if (problems.length > 0) {
  console.error('Phase 6.15.8 frontend build security verification FAILED:')
  for (const problem of problems) console.error(`  - ${problem}`)
  process.exit(1)
}

console.log(
  `Phase 6.15.8 frontend build security verification PASSED ` +
    `(${distFiles.length} dist files scanned; env allowlist: ${[...ALLOWED_ENV_VARS].join(', ')})`,
)
