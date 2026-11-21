import { useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import type { DirectTransferStudent } from '../../../types/transfer.ts'
import { transferReviewIdentity } from '../review/TransferReviewPage.tsx'
import { describeSection } from '../transferLabels.ts'
import DirectTransferForm from './DirectTransferForm.tsx'
import { useDirectTransfer } from './useDirectTransfer.ts'

/** Administrators transfer any student; a Head of Department only within their department. */
export default function DirectTransferPage() {
  const { accessToken, user, role, sessionGeneration } = useAuth()
  if (!accessToken || !user?.institution_id || (role !== 'admin' && role !== 'faculty'))
    return <p role="status">Direct transfers are unavailable for this account.</p>
  const identity = transferReviewIdentity(sessionGeneration, user.user_id, user.institution_id, role)
  return <DirectSession key={identity} identity={identity} institutionId={user.institution_id} token={accessToken} />
}

function matches(student: DirectTransferStudent, search: string) {
  const text = [student.student_name, student.register_number, describeSection(student.current_section)]
    .join(' ')
    .toLocaleLowerCase()
  return text.includes(search.trim().toLocaleLowerCase())
}

function DirectSession({ identity, institutionId, token }: { identity: string; institutionId: string; token: string }) {
  const [selected, setSelected] = useState<DirectTransferStudent | null>(null)
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const { students, options, transfer } = useDirectTransfer(
    identity,
    institutionId,
    token,
    selected?.student_id ?? null,
  )
  const data = students.data
  const error = students.error ?? options.error ?? transfer.error
  const name = selected ? (selected.student_name ?? selected.register_number ?? 'this student') : ''
  return (
    <section className="space-y-5" aria-label="New transfer">
      {data?.can_transfer && (
        <p className="text-muted">
          {data.actor_role === 'admin'
            ? 'Move a student to another section or program. The transfer applies immediately and is recorded in the student’s history.'
            : 'As Head of Department you can move students between sections and programs of your department. The transfer applies immediately.'}
        </p>
      )}
      {students.isPending && <p role="status">Loading students…</p>}
      {error instanceof Error && (
        <div role="alert" className="ui-panel p-4">
          <p>{error.message}</p>
        </div>
      )}
      {notice && <p role="status">{notice}</p>}
      {data && !data.can_transfer && (
        <p role="status">Only administrators and current Heads of Department can transfer students.</p>
      )}
      {data?.can_transfer && !selected && (
        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block font-semibold text-content">Find a student</span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name, register number or section"
              className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-content"
            />
          </label>
          {!data.students.length && <p role="status">No students with a section in an open term are available.</p>}
          <ul className="space-y-2" aria-label="Students">
            {data.students
              .filter((student) => matches(student, search))
              .map((student) => (
                <li key={student.student_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setNotice(null)
                      setSelected(student)
                    }}
                    className="flex min-h-11 w-full flex-col items-start rounded-lg border border-line p-3 text-left hover:bg-hover"
                  >
                    <span className="font-medium text-content">
                      {student.student_name ?? 'Student'}
                      {student.register_number ? ` · ${student.register_number}` : ''}
                    </span>
                    <span className="text-xs text-muted">
                      {describeSection(student.current_section)}
                      {student.has_open_request ? ' · Has an open transfer request' : ''}
                    </span>
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
      {selected && (
        <div className="ui-panel space-y-4 p-4 sm:p-5">
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover"
          >
            Back to students
          </button>
          <h2 className="text-section font-semibold text-content">Transfer {name}</h2>
          {options.isPending && <p role="status">Loading sections…</p>}
          {options.data && (
            <>
              <p className="text-content">Current: {describeSection(options.data.current)}</p>
              {options.data.has_open_request ? (
                <p role="status">
                  {name} has an open transfer request. Approve or reject it under Transfer Requests before moving them
                  directly.
                </p>
              ) : (
                <DirectTransferForm
                  key={selected.student_id}
                  studentName={name}
                  data={options.data}
                  busy={transfer.isPending}
                  onSubmit={(toSectionId, reason, allowOtherSemester) => {
                    const target = options.data?.options.find((item) => item.academic_section_id === toSectionId)
                    transfer.mutate(
                      {
                        student_id: selected.student_id,
                        to_section_id: toSectionId,
                        reason,
                        allow_other_semester: allowOtherSemester,
                      },
                      {
                        onSuccess: () => {
                          setNotice(`${name} was moved to ${target ? describeSection(target) : 'the new section'}.`)
                          setSelected(null)
                        },
                      },
                    )
                  }}
                />
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}
