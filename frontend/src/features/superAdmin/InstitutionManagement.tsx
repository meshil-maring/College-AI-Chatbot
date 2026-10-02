import { useCallback, useEffect, useState } from 'react'
import {
  PlatformInstitutionError,
  activateInstitution,
  assignInstitutionAdmin,
  createInstitution,
  getInstitution,
  listInstitutions,
  suspendInstitution,
} from '../../services/platformInstitutionsApi.ts'
import type {
  InstitutionCreateInput,
  InstitutionDetail,
  InstitutionSummary,
} from '../../types/platform.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import InstitutionDetailPanel, { type BusyAction } from './InstitutionDetailPanel.tsx'

/**
 * Phase 7.13 Super Admin institution management.
 *
 * Desktop-first (1280px+), built on the existing slate/violet design system.
 * Only the Institutions section is implemented; every other platform area stays
 * an honest "Coming Soon" placeholder with no fake functionality.
 *
 * This component holds no authority of its own: it renders only after
 * `SuperAdminShell` received an allow response from `GET /platform/me`, and
 * every action below is independently re-authorized by the backend.
 */

function errorMessage(error: unknown): string {
  if (error instanceof PlatformInstitutionError) return error.message
  return 'Something went wrong. Please try again.'
}

/** The canonical institution lifecycle, reusing the Phase 6.13 status values. */
export function StatusPill({ status }: { status: string }) {
  const label =
    status === 'active' ? 'Active'
      : status === 'suspended' ? 'Suspended'
      : status === 'pending' ? 'Pending'
      : 'Rejected'
  const tone =
    status === 'active'
      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
      : status === 'suspended'
        ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
        : 'border-slate-500/40 bg-slate-500/10 text-slate-300'
  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${tone}`}>{label}</span>
  )
}

const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400'
const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

function InstitutionTable({
  institutions,
  loading,
  onOpen,
}: {
  institutions: InstitutionSummary[]
  loading: boolean
  onOpen: (id: string) => void
}) {
  if (loading) {
    return <p role="status" className="text-sm text-slate-400">Loading institutions...</p>
  }
  if (institutions.length === 0) {
    return (
      <p className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-8 text-center text-sm text-slate-400">
        No institutions have been created yet. Use "Create Institution" to add the first one.
      </p>
    )
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Institutions registered on the platform</caption>
        <thead className="border-b border-slate-700 bg-slate-800/60 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th scope="col" className="px-5 py-3 font-semibold">Institution</th>
            <th scope="col" className="px-5 py-3 font-semibold">Code</th>
            <th scope="col" className="px-5 py-3 font-semibold">Status</th>
            <th scope="col" className="px-5 py-3 font-semibold">Admins</th>
            <th scope="col" className="px-5 py-3 font-semibold"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {institutions.map((institution) => (
            <tr key={institution.id} className="hover:bg-slate-800/40">
              <td className="px-5 py-4 font-medium text-white">{institution.name}</td>
              <td className="px-5 py-4 font-mono text-xs text-slate-400">{institution.code}</td>
              <td className="px-5 py-4"><StatusPill status={institution.status} /></td>
              <td className="px-5 py-4 text-slate-300">{institution.admin_count}</td>
              <td className="px-5 py-4 text-right">
                <button
                  type="button"
                  onClick={() => { onOpen(institution.id) }}
                  className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300"
                >
                  Manage
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CreateInstitutionForm({
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
      className="rounded-2xl border border-slate-700 bg-slate-900 p-6"
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
      <h3 className="text-lg font-semibold text-white">Create institution</h3>
      <p className="mt-1 text-sm text-slate-400">
        Only the name and code are required. Branding can be configured later.
      </p>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div>
          <label className={labelClass} htmlFor="create-name">Institution name</label>
          <input
            id="create-name"
            className={inputClass}
            value={name}
            onChange={(event) => { setName(event.target.value) }}
            placeholder="Unico University"
            required
          />
        </div>
        <div>
          <label className={labelClass} htmlFor="create-code">Institution code</label>
          <input
            id="create-code"
            className={inputClass}
            value={code}
            onChange={(event) => { setCode(event.target.value) }}
            placeholder="UNICO"
            required
          />
          <p className="mt-1 text-xs text-slate-500">
            2-32 characters: letters, digits, hyphens or underscores. Used in the public URL.
          </p>
        </div>
        <div>
          <label className={labelClass} htmlFor="create-display">Display name (optional)</label>
          <input
            id="create-display"
            className={inputClass}
            value={displayName}
            onChange={(event) => { setDisplayName(event.target.value) }}
            placeholder="Unico"
          />
        </div>
        <div>
          <label className={labelClass} htmlFor="create-welcome">Welcome message (optional)</label>
          <input
            id="create-welcome"
            className={inputClass}
            value={welcomeMessage}
            onChange={(event) => { setWelcomeMessage(event.target.value) }}
            placeholder="Welcome to Unico University."
          />
        </div>
      </div>
      <div className="mt-6 flex items-center gap-3">
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
        >
          {busy ? 'Creating...' : 'Create institution'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

export default function InstitutionManagement() {
  const { accessToken } = useAuth()
  const [institutions, setInstitutions] = useState<InstitutionSummary[]>([])
  const [selected, setSelected] = useState<InstitutionDetail | null>(null)
  const [showDetail, setShowDetail] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<BusyAction>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const token = accessToken ?? ''

  const refreshList = useCallback(async (): Promise<void> => {
    if (token === '') return
    setLoading(true)
    try {
      setInstitutions(await listInstitutions(token))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void refreshList()
  }, [refreshList])

  const openDetail = useCallback(
    async (institutionId: string): Promise<void> => {
      setLoading(true)
      setError(null)
      try {
        setSelected(await getInstitution(token, institutionId))
        setShowDetail(true)
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    },
    [token],
  )

  /** Every mutation re-reads the authoritative server state afterwards. */
  const runAction = useCallback(
    async (action: BusyAction, operation: () => Promise<string>): Promise<void> => {
      setBusy(action)
      setError(null)
      setNotice(null)
      try {
        setNotice(await operation())
        await refreshList()
        if (selected !== null) setSelected(await getInstitution(token, selected.id))
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setBusy(null)
      }
    },
    [refreshList, selected, token],
  )

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-300">Platform</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Institutions</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Manage the universities and colleges registered on the platform. This view shows
            platform metadata only and never exposes student data.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {showDetail ? (
            <button
              type="button"
              onClick={() => { setShowDetail(false); setSelected(null); setError(null); setNotice(null) }}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300"
            >
              Back to all institutions
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => { setShowCreate((open) => !open); setError(null); setNotice(null) }}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300"
          >
            + Create Institution
          </button>
        </div>
      </header>

      {error !== null ? (
        <p role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </p>
      ) : null}
      {notice !== null ? (
        <p role="status" className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
          {notice}
        </p>
      ) : null}

      {showCreate ? (
        <CreateInstitutionForm
          busy={busy === 'create'}
          onCancel={() => { setShowCreate(false) }}
          onSubmit={async (input) => {
            await runAction('create', async () => {
              const created = await createInstitution(token, input)
              setShowCreate(false)
              await openDetail(created.id)
              return `Institution ${created.name} created. Public AI is reachable at /u/${created.code.toLowerCase()}/ai.`
            })
          }}
        />
      ) : null}

      {showDetail && selected !== null ? (
        <InstitutionDetailPanel
          institution={selected}
          busy={busy}
          onSaved={(detail) => { setSelected(detail); void refreshList() }}
          onSuspend={() =>
            void runAction('suspend', async () => (await suspendInstitution(token, selected.id)).message)
          }
          onActivate={() =>
            void runAction('activate', async () => (await activateInstitution(token, selected.id)).message)
          }
          onAssign={(email) =>
            void runAction('assign', async () => {
              const result = await assignInstitutionAdmin(token, selected.id, email)
              return result.already_assigned
                ? `${result.admin.email} already manages this institution.`
                : `${result.admin.email} is now a University Admin of this institution.`
            })
          }
        />
      ) : (
        <InstitutionTable institutions={institutions} loading={loading} onOpen={(id) => { void openDetail(id) }} />
      )}
    </div>
  )
}
