import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useAcademicPackages } from './useAcademicPackages.ts'
import { canManage } from './packagePresentation.ts'
import CurriculumSetup from './setup/CurriculumSetup.tsx'
import ClassSetup from './setup/ClassSetup.tsx'
import PackageAssignments from './assignments/PackageAssignments.tsx'
import PackageRequests from './assignments/PackageRequests.tsx'
import PackageHistory from './assignments/PackageHistory.tsx'
import '../admin/academic-setup/styles/academic-setup.css'
import './styles/packages.css'

type PackageView = 'curricula' | 'classes' | 'assignments' | 'requests' | 'history'

export default function AcademicPackagesWorkspace({
  accessToken,
  initialView = 'assignments',
  selfService = false,
  embeddedView,
  onBusyChange,
  onCreateProgram,
}: {
  accessToken: string
  initialView?: PackageView
  selfService?: boolean
  embeddedView?: 'curricula' | 'classes' | 'assignments'
  onBusyChange?: (busy: boolean) => void
  onCreateProgram?: () => void
}) {
  return (
    <PackageWorkspace
      key={accessToken}
      accessToken={accessToken}
      initialView={embeddedView ?? initialView}
      selfService={selfService}
      embeddedView={embeddedView}
      onBusyChange={onBusyChange}
      onCreateProgram={onCreateProgram}
    />
  )
}

function PackageWorkspace({
  accessToken,
  initialView,
  selfService,
  embeddedView,
  onBusyChange,
  onCreateProgram,
}: {
  accessToken: string
  initialView: PackageView
  selfService: boolean
  embeddedView?: 'curricula' | 'classes' | 'assignments'
  onBusyChange?: (busy: boolean) => void
  onCreateProgram?: () => void
}) {
  const state = useAcademicPackages(accessToken)
  const [view, setView] = useState<PackageView>(initialView)
  const data = state.data
  useEffect(() => {
    onBusyChange?.(state.busy)
  }, [state.busy, onBusyChange])
  const navigation: { key: PackageView; label: string }[] = [
    ...(!selfService && data && (canManage(data, 'curriculum') || Boolean(data.records.curricula?.length))
      ? [{ key: 'curricula' as const, label: 'Named curricula & packages' }]
      : []),
    ...(!selfService && data && (canManage(data, 'class') || Boolean(data.records.classes?.length))
      ? [{ key: 'classes' as const, label: 'Class Setup' }]
      : []),
    { key: 'assignments', label: 'Package Assignment' },
    { key: 'requests', label: 'Change Requests' },
    { key: 'history', label: 'History' },
  ]
  const visibleNavigation = embeddedView
    ? navigation.filter((item) => ['assignments', 'requests', 'history'].includes(item.key))
    : navigation
  const activeView =
    embeddedView && embeddedView !== 'assignments'
      ? embeddedView
      : navigation.some((item) => item.key === view)
        ? view
        : 'assignments'
  return (
    <section
      className={`${embeddedView ? 'package-embedded' : 'academic-setup'} package-workspace`}
      aria-label="Academic curriculum and package workspace"
    >
      <header className="package-heading">
        {!embeddedView && (
          <div>
            <h2>Curriculum & subject packages</h2>
            <p>One class, shared core subjects and complete subject combinations.</p>
          </div>
        )}
        <button
          type="button"
          className="academic-secondary"
          disabled={state.busy || state.query.isFetching}
          onClick={() => void state.query.refetch()}
        >
          <RefreshCw aria-hidden="true" /> Refresh packages
        </button>
      </header>
      {state.query.isPending && <p role="status">Loading academic packages…</p>}
      {state.query.isError && (
        <p role="alert" className="academic-error">
          {state.query.error.message}
        </p>
      )}
      {state.error && (
        <p role="alert" className="academic-error">
          {state.error.message}
        </p>
      )}
      {state.notice && (
        <p role="status" className="academic-success">
          {state.notice}
        </p>
      )}
      {data && !state.query.isError && (
        <>
          {(!embeddedView || embeddedView === 'assignments') && (
            <nav
              className="academic-tabs"
              aria-label={embeddedView ? 'Assignment operations' : 'Curriculum and package pages'}
            >
              {visibleNavigation.map((item) => (
                <button
                  type="button"
                  key={item.key}
                  aria-current={activeView === item.key ? 'page' : undefined}
                  disabled={state.busy}
                  onClick={() => {
                    setView(item.key)
                    state.clearError()
                  }}
                >
                  {embeddedView && item.key === 'assignments' ? 'Student assignments' : item.label}
                </button>
              ))}
            </nav>
          )}
          {activeView === 'curricula' && (
            <CurriculumSetup data={data} state={state} onCreateProgram={onCreateProgram} />
          )}
          {activeView === 'classes' && <ClassSetup data={data} state={state} onCreateProgram={onCreateProgram} />}
          {activeView === 'assignments' && <PackageAssignments data={data} state={state} />}
          {activeView === 'requests' && <PackageRequests data={data} state={state} />}
          {activeView === 'history' && <PackageHistory data={data} />}
        </>
      )}
    </section>
  )
}
