import { RefreshCw } from 'lucide-react'
import { StudentsSearch } from './StudentsUI.tsx'
import type { ApprovalQueueModel } from './useStudentApprovalQueue.ts'

export default function StudentApprovalToolbar({ model }: { model: ApprovalQueueModel }) {
  const { draftSearch, setDraftSearch, setSearch, setPage, search, refresh, queue, busyStudentId } = model
  return (
    <div className="students-toolbar">
      <div className="students-toolbar-heading">
        <h2>Pending registrations</h2>
        <p>Student registrations awaiting a decision for your institution.</p>
      </div>
      <div className="students-table-actions">
        <StudentsSearch
          value={draftSearch}
          onChange={setDraftSearch}
          onSubmit={() => {
            setSearch(draftSearch.trim())
            setPage(0)
          }}
          label="Search pending registrations"
          placeholder="Student number, register number, roll number or email"
        />
        {search && (
          <button
            type="button"
            className="students-button"
            onClick={() => {
              setSearch('')
              setDraftSearch('')
              setPage(0)
            }}
          >
            Clear filters
          </button>
        )}
        <button
          type="button"
          className="students-button"
          onClick={refresh}
          disabled={queue.isFetching || busyStudentId !== null}
        >
          <RefreshCw aria-hidden="true" />
          {queue.isFetching && !queue.isPending ? 'Refreshing…' : 'Refresh registrations'}
        </button>
      </div>
    </div>
  )
}
