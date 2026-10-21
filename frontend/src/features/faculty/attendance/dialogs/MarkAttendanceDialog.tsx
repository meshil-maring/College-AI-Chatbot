import { Modal, ModalActions, NoAssignmentWorkflow } from './AttendanceDialog.tsx'
import { input } from '../shared/AttendanceWorkspaceUi.tsx'
import type { FacultyAttendanceWorkspaceModel } from '../state/useAttendanceWorkspace.ts'
import { type AttendanceValue } from '../state/workspaceTypes.ts'
export function MarkAttendanceDialog({ model }: { model: FacultyAttendanceWorkspaceModel }) {
  const {
    onNavigateAssignments,
    statuses,
    setStatuses,
    sessionDate,
    setSessionDate,
    markOpen,
    setMarkOpen,
    markPage,
    setMarkPage,
    saving,
    selected,
    roster,
    canManage,
    saveAttendance,
  } = model
  return (
    <>
      {markOpen ? (
        <Modal title="Mark Attendance" onClose={() => setMarkOpen(false)}>
          {selected && canManage ? (
            <>
              <p className="text-sm text-slate-400">
                Record attendance for {selected.section.course.name} · {selected.section.name}.
              </p>
              <label className="mt-4 block text-xs font-semibold text-slate-300">
                Session date
                <input
                  aria-label="Attendance date"
                  type="date"
                  value={sessionDate}
                  onChange={(event) => setSessionDate(event.target.value)}
                  className={`${input} mt-1 block w-full`}
                />
              </label>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setStatuses(
                      Object.fromEntries(
                        roster.slice(markPage * 500, (markPage + 1) * 500).map((row) => [row.roster_id, 'present']),
                      ),
                    )
                  }
                  className="rounded-lg border border-[#2c4964] px-3 py-2 text-xs text-slate-200"
                >
                  Mark all present
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setStatuses(
                      Object.fromEntries(
                        roster.slice(markPage * 500, (markPage + 1) * 500).map((row) => [row.roster_id, 'absent']),
                      ),
                    )
                  }
                  className="rounded-lg border border-[#2c4964] px-3 py-2 text-xs text-slate-200"
                >
                  Mark all absent
                </button>
              </div>
              <div className="mt-4 max-h-52 space-y-2 overflow-y-auto pr-1">
                {roster.slice(markPage * 500, (markPage + 1) * 500).map((row) => (
                  <div
                    key={row.roster_id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-[#1e3348] bg-[#091725] px-3 py-2"
                  >
                    <span className="truncate text-xs text-slate-200">
                      {row.student_name}
                      <span className="ml-2 text-slate-500">{row.register_number}</span>
                    </span>
                    <select
                      aria-label={`Attendance for ${row.student_name}`}
                      value={statuses[row.roster_id] ?? ''}
                      onChange={(event) =>
                        setStatuses((previous) => {
                          const next = { ...previous }
                          if (event.target.value) next[row.roster_id] = event.target.value as AttendanceValue
                          else delete next[row.roster_id]
                          return next
                        })
                      }
                      className="rounded border border-[#304862] bg-[#102235] px-2 py-1 text-xs text-white"
                    >
                      <option value="">Not marked</option>
                      {(['present', 'absent', 'late', 'excused'] as AttendanceValue[]).map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex justify-between gap-2 text-xs text-slate-400">
                <span>Roster page {markPage + 1} ? up to 500 students per submission</span>
                <button
                  type="button"
                  disabled={markPage === 0}
                  onClick={() => {
                    setStatuses({})
                    setMarkPage((value) => value - 1)
                  }}
                >
                  Previous roster page
                </button>
                <button
                  type="button"
                  disabled={(markPage + 1) * 500 >= roster.length}
                  onClick={() => {
                    setStatuses({})
                    setMarkPage((value) => value + 1)
                  }}
                >
                  Next roster page
                </button>
              </div>
              <ModalActions
                onCancel={() => setMarkOpen(false)}
                submitLabel="Save Attendance"
                onSubmit={() => void saveAttendance()}
                saving={saving}
              />
            </>
          ) : (
            <NoAssignmentWorkflow
              action="mark attendance"
              onNavigateAssignments={onNavigateAssignments}
              onClose={() => setMarkOpen(false)}
            />
          )}
        </Modal>
      ) : null}
    </>
  )
}
