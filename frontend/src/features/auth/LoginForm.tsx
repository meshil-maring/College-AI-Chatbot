/**
 * Phase 5.4 — Minimal login UI.
 *
 * Collects exactly the fields the backend login contract requires
 * (email + password) and submits them through the auth service. The JWT is
 * never rendered, nothing is logged, and the password is never persisted.
 */

import { useEffect, useState } from 'react'
import { useAuth } from './AuthProvider.tsx'
import ForgotPasswordForm from './ForgotPasswordForm.tsx'
import { fetchDevAuthStatus } from '../../services/devAuth.ts'

export default function LoginForm() {
  const { status, error, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [devTestModeEnabled, setDevTestModeEnabled] = useState(false)

  useEffect(() => {
    // DEVELOPMENT / TESTING ONLY — "Forgot Password?" only appears when the
    // backend explicitly reports dev/test mode is enabled.
    let cancelled = false
    void fetchDevAuthStatus().then((result) => {
      if (!cancelled) setDevTestModeEnabled(result.dev_test_mode)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const busy = status === 'authenticating'

  if (showForgotPassword) {
    return <ForgotPasswordForm onBackToLogin={() => setShowForgotPassword(false)} />
  }


  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-md w-full py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white tracking-tight">College AI Chatbot</h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Sign in to continue. Authentication is handled entirely by the backend.
          </p>

          {error !== null && (
            <div
              role="alert"
              className="mt-5 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-400"
            >
              {error}
            </div>
          )}

          <form
            className="mt-6 flex flex-col gap-5"
            onSubmit={(event) => {
              event.preventDefault()
              if (busy) return
              void login(email, password)
            }}
          >
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Email
              <input
                type="email"
                name="email"
                required
                autoComplete="email"
                disabled={busy}
                placeholder="student@college.edu"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-slate-300">
              Password
              <input
                type="password"
                name="password"
                required
                minLength={6}
                autoComplete="current-password"
                disabled={busy}
                placeholder="••••••••"
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
            {devTestModeEnabled && (
              <button
                type="button"
                disabled={busy}
                onClick={() => setShowForgotPassword(true)}
                className="text-sm text-slate-400 hover:text-slate-200 underline"
              >
                Forgot password? (Dev/Test only)
              </button>
            )}
          </form>

          <p className="mt-6 text-xs text-slate-500">
            Phase 5.4 — authentication &amp; session bootstrap. The chat
            interface arrives in a later phase.
          </p>
        </div>
      </main>
    </div>
  )
}