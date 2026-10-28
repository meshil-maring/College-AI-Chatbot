import { useState } from 'react'
import type { InstitutionCreateInput } from '../../../types/platform.ts'
import { inputClass, labelClass } from './InstitutionTable.tsx'
export function CreateInstitutionForm({
  busy,
  onCancel,
  onSubmit,
}: {
  busy: boolean
  onCancel: () => void
  onSubmit: (input: InstitutionCreateInput) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [welcomeMessage, setWelcomeMessage] = useState('')

  const canSubmit = name.trim() !== '' && code.trim() !== '' && !busy

  return (
    <form
      className="rounded-xl border border-line bg-surface p-6"
      onSubmit={(event) => {
        event.preventDefault()
        if (!canSubmit) return
        void onSubmit({
          name: name.trim(),
          code: code.trim(),
          ...(displayName.trim() !== '' ? { display_name: displayName.trim() } : {}),
          ...(welcomeMessage.trim() !== '' ? { welcome_message: welcomeMessage.trim() } : {}),
        })
      }}
    >
      <h3 className="font-semibold text-content text-card">Create institution</h3>
      <p className="mt-1 text-sm text-muted">Only the name and code are required. Branding can be configured later.</p>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div>
          <label className={labelClass} htmlFor="create-name">
            Institution name
          </label>
          <input
            id="create-name"
            className={inputClass}
            value={name}
            onChange={(event) => {
              setName(event.target.value)
            }}
            placeholder="Unico University"
            required
          />
        </div>
        <div>
          <label className={labelClass} htmlFor="create-code">
            Institution code
          </label>
          <input
            id="create-code"
            className={inputClass}
            value={code}
            onChange={(event) => {
              setCode(event.target.value)
            }}
            placeholder="UNICO"
            required
          />
          <p className="mt-1 text-xs text-muted">
            2-32 characters: letters, digits, hyphens or underscores. Used in the public URL.
          </p>
        </div>
        <div>
          <label className={labelClass} htmlFor="create-display">
            Display name (optional)
          </label>
          <input
            id="create-display"
            className={inputClass}
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value)
            }}
            placeholder="Unico"
          />
        </div>
        <div>
          <label className={labelClass} htmlFor="create-welcome">
            Welcome message (optional)
          </label>
          <input
            id="create-welcome"
            className={inputClass}
            value={welcomeMessage}
            onChange={(event) => {
              setWelcomeMessage(event.target.value)
            }}
            placeholder="Welcome to Unico University."
          />
        </div>
      </div>
      <div className="mt-6 flex items-center gap-3">
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
        >
          {busy ? 'Creating...' : 'Create institution'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-control px-4 py-2 text-sm font-medium text-muted hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
