import { useState } from 'react'

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{32,256}$/

/** Accepts a full invitation link or the bare code and extracts the token. */
export function extractSuperAdminInviteToken(value: string): string | null {
  const trimmed = value.trim()
  const fromLink = trimmed.match(/\/super-admin-invite\/([^/?#\s]+)/)
  const candidate = fromLink !== null ? fromLink[1] : trimmed
  return TOKEN_PATTERN.test(candidate) ? candidate : null
}

/**
 * Entry point for Super Admin registration (`/register/super-admin`).
 * Registration is invitation-only: the invitee supplies the link they were
 * given, and the server validates it on the next page.
 */
export default function SuperAdminRegisterEntryPage() {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)

  const submit = (event: React.FormEvent): void => {
    event.preventDefault()
    const token = extractSuperAdminInviteToken(value)
    if (token === null) {
      setError('Enter the full invitation link or code you received.')
      return
    }
    window.location.assign(`/super-admin-invite/${encodeURIComponent(token)}`)
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-content">
      <section className="w-full max-w-lg rounded-xl border border-line bg-surface p-8 shadow-none">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Platform administration</p>
        <h1 className="mt-2 font-bold text-page">Register as Super Admin</h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          Super Admin accounts are invitation-only. Ask an existing Super Admin to invite your email address, then paste
          the single-use link or code you were given.
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <div>
            <label htmlFor="sa-invite" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Invitation link or code
            </label>
            <input
              id="sa-invite"
              value={value}
              maxLength={600}
              autoComplete="off"
              onChange={(e) => {
                setValue(e.target.value)
                setError(null)
              }}
              className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
          {error !== null ? (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover"
          >
            Continue
          </button>
        </form>
        <p className="mt-6 text-sm text-muted">
          Already registered?{' '}
          <a href="/super-admin" className="text-accent underline">
            Super Admin login
          </a>
        </p>
      </section>
    </main>
  )
}
