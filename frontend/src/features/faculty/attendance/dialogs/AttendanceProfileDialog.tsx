import { Modal } from './AttendanceDialog.tsx'
import { AttendanceStatusBadge } from '../shared/AttendancePrimitives.tsx'
import { AttendanceStudentHistory } from '../roster/AttendanceRecordedViews.tsx'
import { formatPercent, Glyph, importedStats, ProfileStat } from '../shared/AttendanceWorkspaceUi.tsx'
import type { FacultyAttendanceWorkspaceModel } from '../state/useAttendanceWorkspace.ts'
export function AttendanceProfileDialog({ model }: { model: FacultyAttendanceWorkspaceModel }) {
  const { accessToken, profile, setProfile } = model
  return (
    <>
      {profile ? (
        <Modal title="Student Attendance Profile" onClose={() => setProfile(null)}>
          <button
            type="button"
            onClick={() => setProfile(null)}
            className="mb-4 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-white"
          >
            <Glyph name="back" size={14} />
            Back to Students
          </button>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#2a3d54] font-bold text-white">
              {profile.student_name
                .split(' ')
                .map((part) => part[0])
                .join('')
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div>
              <h2 className="font-bold text-white">{profile.student_name}</h2>
              <p className="text-xs text-slate-400">
                {profile.register_number} · {profile.university_roll_number ?? 'No university roll number'}
              </p>
            </div>
          </div>
          <div className="mt-4">
            <AttendanceStatusBadge row={profile} percentage={importedStats(profile).percentage} />
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <ProfileStat label="Classes" value={importedStats(profile).classes} />
            <ProfileStat label="Present" value={importedStats(profile).present} />
            <ProfileStat label="Absent" value={importedStats(profile).absent} />
            <ProfileStat label="Attendance" value={formatPercent(importedStats(profile).percentage)} />
          </div>
          <AttendanceStudentHistory token={accessToken} student={profile} />
        </Modal>
      ) : null}
    </>
  )
}
