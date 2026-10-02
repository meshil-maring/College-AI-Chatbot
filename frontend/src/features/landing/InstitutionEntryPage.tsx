import { useState } from 'react'
import { lookupInstitution, RegistrationError, registrationErrorMessage } from '../../services/registration.ts'

const INSTITUTION_CODE_PATTERN = /^[A-Z0-9][A-Z0-9_-]{0,31}$/

export function normalizeInstitutionCode(rawCode: string): string | null {
  const code = rawCode.trim().toUpperCase()
  return INSTITUTION_CODE_PATTERN.test(code) ? code : null
}

export default function InstitutionEntryPage() {
  const [code, setCode] = useState('')
  const [status, setStatus] = useState<'idle' | 'checking' | 'error'>('idle')
  const [message, setMessage] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (status === 'checking') return
    const normalized = normalizeInstitutionCode(code)
    if (normalized === null) {
      setStatus('error')
      setMessage('Enter the institution code supplied by your university.')
      return
    }

    setStatus('checking')
    setMessage(null)
    try {
      const institution = await lookupInstitution(normalized)
      const destination = `/u/${encodeURIComponent(institution.code.toLowerCase())}`
      window.history.pushState({}, '', destination)
      window.dispatchEvent(new PopStateEvent('popstate'))
    } catch (error) {
      setStatus('error')
      setMessage(
        error instanceof RegistrationError
          ? registrationErrorMessage(error)
          : 'Could not find that institution right now. Please try again.',
      )
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <a href="/" className="rounded-md text-lg font-bold text-white focus:outline-none focus:ring-2 focus:ring-emerald-300">College AI</a>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-bold tracking-[0.18em] text-emerald-300">DEMO</span>
        </div>
      </header>
      <main className="mx-auto flex max-w-5xl items-center justify-center px-6 py-20">
        <section className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl" aria-labelledby="choose-institution-heading">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Public university gateway</p>
          <h1 id="choose-institution-heading" className="mt-3 text-3xl font-bold text-white">Choose Institution</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">Enter the public code provided by your university. The platform verifies it before opening the institution page.</p>

          {message !== null ? <p role="alert" className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-3 text-sm text-red-300">{message}</p> : null}

          <form className="mt-7" onSubmit={(event) => void handleSubmit(event)} aria-busy={status === 'checking'} noValidate>
            <label htmlFor="institution-code" className="block text-sm font-medium text-slate-200">Institution code</label>
            <input
              id="institution-code"
              name="institution_code"
              value={code}
              onChange={(event) => {
                setCode(event.target.value)
                setMessage(null)
                setStatus('idle')
              }}
              autoComplete="off"
              placeholder="e.g. GIT"
              disabled={status === 'checking'}
              className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-950 px-4 py-3 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400 disabled:opacity-60"
            />
            <button type="submit" disabled={status === 'checking'} className="mt-4 w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-60">
              {status === 'checking' ? 'Checking institution…' : 'Continue'}
            </button>
          </form>
          <a href="/" className="mt-6 inline-block rounded-sm text-sm text-slate-400 underline hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-300">Back to platform gateway</a>
        </section>
      </main>
    </div>
  )
}

