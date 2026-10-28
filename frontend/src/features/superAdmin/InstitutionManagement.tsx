import { useCallback, useEffect, useState } from 'react'
import {
  PlatformInstitutionError,
  activateInstitution,
  assignInstitutionAdmin,
  createInstitution,
  getInstitution,
  listInstitutions,
  suspendInstitution,
} from '../../services/platform/platformInstitutionsApi.ts'
import type { InstitutionDetail, InstitutionSummary } from '../../types/platform.ts'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import InstitutionDetailPanel, { type BusyAction } from './InstitutionDetailPanel.tsx'
import { CreateInstitutionForm } from './institutions/CreateInstitutionForm.tsx'
import { InstitutionTable } from './institutions/InstitutionTable.tsx'

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
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Platform</p>
          <h1 className="mt-2 font-bold text-content text-page">Institutions</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            Manage the universities and colleges registered on the platform. This view shows platform metadata only and
            never exposes student data.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {showDetail ? (
            <button
              type="button"
              onClick={() => {
                setShowDetail(false)
                setSelected(null)
                setError(null)
                setNotice(null)
              }}
              className="rounded-lg border border-control px-4 py-2 text-sm font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Back to all institutions
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              setShowCreate((open) => !open)
              setError(null)
              setNotice(null)
            }}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
          >
            + Create Institution
          </button>
        </div>
      </header>

      {error !== null ? (
        <p role="alert" className="rounded-xl border border-danger bg-danger-bg px-4 py-3 text-sm text-danger">
          {error}
        </p>
      ) : null}
      {notice !== null ? (
        <p role="status" className="rounded-xl border border-success bg-success-bg px-4 py-3 text-sm text-success">
          {notice}
        </p>
      ) : null}

      {showCreate ? (
        <CreateInstitutionForm
          busy={busy === 'create'}
          onCancel={() => {
            setShowCreate(false)
          }}
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
          onSaved={(detail) => {
            setSelected(detail)
            void refreshList()
          }}
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
        <InstitutionTable
          institutions={institutions}
          loading={loading}
          onOpen={(id) => {
            void openDetail(id)
          }}
        />
      )}
    </div>
  )
}

export { StatusPill } from './institutions/InstitutionTable.tsx'
