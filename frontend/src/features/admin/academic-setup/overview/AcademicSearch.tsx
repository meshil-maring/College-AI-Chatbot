import { Search, X } from 'lucide-react'

export default function AcademicSearch({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="admin-global-search academic-global-search" role="search">
      <Search aria-hidden="true" />
      <input
        type="search"
        aria-label="Search academic setup"
        aria-controls="academic-overview-results"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search departments, programs, subjects, curricula, or academic records..."
      />
      {value && (
        <button type="button" aria-label="Clear academic search" onClick={() => onChange('')}>
          <X aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
