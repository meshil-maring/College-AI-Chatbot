import { useState } from 'react'
import {
  lookupInstitution,
  RegistrationError,
  registrationErrorMessage,
} from '../../services/registration/registration.ts'

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
    <div className="min-h-screen bg-canvas text-content">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <a
            href="/"
            className="rounded-md text-lg font-bold text-content focus:outline-none focus:ring-2 focus:ring-accent"
          >
            College AI
          </a>
          <span className="rounded-full border border-accent bg-raised px-3 py-1 text-xs font-bold tracking-[0.18em] text-accent">
            DEMO
          </span>
        </div>
      </header>
      <main className="mx-auto flex max-w-5xl items-center justify-center px-6 py-20">
        <section
          className="w-full max-w-xl rounded-xl border border-line bg-surface p-8 shadow-none"
          aria-labelledby="choose-institution-heading"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Public university gateway</p>
          <h1 id="choose-institution-heading" className="mt-3 font-bold text-content text-page">
            Choose Institution
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            Enter the public code provided by your university. The platform verifies it before opening the institution
            page.
          </p>

          {message !== null ? (
            <p role="alert" className="mt-5 rounded-lg border border-danger bg-danger-bg px-4 py-3 text-sm text-danger">
              {message}
            </p>
          ) : null}

          <form
            className="mt-7"
            onSubmit={(event) => void handleSubmit(event)}
            aria-busy={status === 'checking'}
            noValidate
          >
            <label htmlFor="institution-code" className="block text-sm font-medium text-content">
              Institution code
            </label>
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
              className="mt-2 w-full rounded-lg border border-control bg-canvas px-4 py-3 text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={status === 'checking'}
              className="mt-4 w-full rounded-lg bg-accent px-4 py-3 font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {status === 'checking' ? 'Checking institution…' : 'Continue'}
            </button>
          </form>
          <a
            href="/"
            className="mt-6 inline-block rounded-sm text-sm text-muted underline hover:text-content focus:outline-none focus:ring-2 focus:ring-accent"
          >
            Back to platform gateway
          </a>
        </section>
      </main>
    </div>
  )
}
