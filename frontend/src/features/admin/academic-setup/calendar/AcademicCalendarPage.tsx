import { useEffect, useRef } from 'react'
import { CalendarDays, ChevronRight, Plus } from 'lucide-react'
import { calendarTabs, type CalendarTab } from './calendarModel.ts'
import { useCalendar, type CalendarContext } from './useCalendar.ts'
import { useCalendarEditor } from './useCalendarEditor.ts'
import CalendarSummary from './CalendarSummary.tsx'
import CalendarFilters from './CalendarFilters.tsx'
import CalendarYears from './CalendarYears.tsx'
import CalendarSemesters from './CalendarSemesters.tsx'
import CalendarSchedule from './CalendarSchedule.tsx'
import CalendarPagination from './CalendarPagination.tsx'
import CalendarDrawer from './editor/CalendarDrawer.tsx'
import './styles/calendar.css'

interface Props extends CalendarContext {
  initialTab: CalendarTab
  createInitially: boolean
  onCreateHandled: () => void
  onOverview: () => void
}
export default function AcademicCalendarPage({
  initialTab,
  createInitially,
  onCreateHandled,
  onOverview,
  ...context
}: Props) {
  const state = useCalendar(context, initialTab)
  const editor = useCalendarEditor(context, state)
  const tabs = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!createInitially || state.loading) return
    if (state.canManageYears && !state.busy) editor.open('academic_years', 'add')
    onCreateHandled()
  }, [createInitially, state.loading, state.canManageYears, state.busy, editor, onCreateHandled])
  const records = state.tab === 'semesters' ? state.semesters : state.years
  return (
    <section
      className={`academic-workspace calendar-page${editor.panel ? ' has-drawer' : ''}`}
      aria-label="Academic calendar management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Academic Calendar</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Academic Calendar</h1>
          <p>Manage academic years, semesters and important academic dates.</p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canManageYears || state.busy || editor.saving}
          onClick={() => editor.open('academic_years', 'add')}
        >
          <Plus aria-hidden="true" /> Add Academic Year
        </button>
      </header>
      <CalendarSummary state={state} />
      {(!context.canReadCatalogues || (records && !state.canManageYears && !state.canManageSemesters)) && (
        <p className="calendar-access-note" role="status">
          {!context.canReadCatalogues
            ? 'Your account does not have academic catalogue access. Records and actions are unavailable.'
            : 'Read-only access. You can view the academic calendar; changes are unavailable.'}
        </p>
      )}
      {state.error && (
        <div className="academic-request-error" role="alert">
          <p>
            {records
              ? 'Could not refresh the calendar. Showing the last loaded records; changes are unavailable until Retry succeeds.'
              : state.error}
          </p>
          <button
            type="button"
            className="academic-secondary-button"
            disabled={state.query.isFetching}
            onClick={() => void state.query.refetch()}
          >
            Retry
          </button>
        </div>
      )}
      {editor.notice && (
        <p className="calendar-save-notice" role="status">
          {editor.notice}
        </p>
      )}
      <div
        ref={tabs}
        className="calendar-tabs"
        role="tablist"
        aria-label="Academic calendar views"
        onKeyDown={(event) => {
          const index = calendarTabs.findIndex((tab) => tab.id === state.tab)
          const next =
            event.key === 'ArrowRight'
              ? (index + 1) % 4
              : event.key === 'ArrowLeft'
                ? (index + 3) % 4
                : event.key === 'Home'
                  ? 0
                  : event.key === 'End'
                    ? 3
                    : -1
          if (next < 0) return
          event.preventDefault()
          state.setTab(calendarTabs[next].id)
          tabs.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus()
        }}
      >
        {calendarTabs.map((tab) => (
          <button
            type="button"
            role="tab"
            id={`calendar-tab-${tab.id}`}
            key={tab.id}
            aria-controls="calendar-panel"
            aria-selected={state.tab === tab.id}
            tabIndex={state.tab === tab.id ? 0 : -1}
            onClick={() => state.setTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <CalendarFilters state={state} />
      <div id="calendar-panel" role="tabpanel" aria-labelledby={`calendar-tab-${state.tab}`}>
        {state.loading ? (
          <div className="calendar-empty" role="status">
            Loading academic calendar...
          </div>
        ) : !records ? (
          <div className="calendar-empty">
            <CalendarDays aria-hidden="true" />
            <h2>Calendar records unavailable</h2>
            <p>Your account cannot currently view these records.</p>
          </div>
        ) : !state.count ? (
          <div className="calendar-empty">
            <CalendarDays aria-hidden="true" />
            <h2>
              {records.length
                ? 'No matching records'
                : `No ${state.tab === 'semesters' ? 'semesters' : 'academic years'} yet`}
            </h2>
            <p>
              {records.length
                ? 'Try another search or status filter.'
                : 'Add an academic year and configure its semesters to get started.'}
            </p>
            {records.length > 0 && (
              <button type="button" className="academic-secondary-button" onClick={state.clearFilters}>
                Clear filters
              </button>
            )}
          </div>
        ) : state.tab === 'years' ? (
          <CalendarYears state={state} editor={editor} />
        ) : state.tab === 'semesters' ? (
          <CalendarSemesters records={state.semesterRows} state={state} editor={editor} showYear />
        ) : (
          <CalendarSchedule state={state} editor={editor} />
        )}
      </div>
      {state.tab === 'semesters' && records && (
        <button
          type="button"
          className="calendar-outline-button calendar-add-semester"
          disabled={
            !state.canManageSemesters || state.busy || !state.years?.some((year) => year.is_active) || editor.saving
          }
          onClick={() => editor.open('semesters', 'add')}
        >
          <Plus aria-hidden="true" /> Add Semester
        </button>
      )}
      {records && !state.loading && (state.tab === 'years' || state.tab === 'semesters') && (
        <CalendarPagination state={state} />
      )}
      {editor.panel && (editor.panel.entity === 'academic_years' ? state.years : state.semesters) && (
        <CalendarDrawer editor={editor} state={state} />
      )}
    </section>
  )
}
