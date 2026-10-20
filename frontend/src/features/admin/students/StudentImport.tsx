import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSpreadsheet,
  Files,
  Filter,
  Info,
  Search,
  Upload,
} from 'lucide-react'
import type { Student } from '../../../types/admin.ts'
import {
  downloadCsv,
  IMPORT_COLUMNS,
  readStudentFile,
  validateStudents,
  type ImportStudent,
  type ReviewStatus,
  type ReviewStudent,
} from './studentImport.ts'

const statuses = {
  valid: {
    label: 'Valid',
    title: 'Valid Records',
    description: 'Ready to import',
    Icon: CheckCircle2,
  },
  duplicate: {
    label: 'Duplicate',
    title: 'Duplicate Records',
    description: 'Already exist in system',
    Icon: Files,
  },
  invalid: {
    label: 'Invalid',
    title: 'Invalid Records',
    description: 'Missing required fields',
    Icon: AlertTriangle,
  },
  conflicting: {
    label: 'Conflicting',
    title: 'Conflicting Records',
    description: 'Data mismatch with existing',
    Icon: AlertCircle,
  },
} as const
const steps = [
  ['Upload File', 'Select and upload'],
  ['Validate & Preview', 'Check records'],
  ['Confirm Import', 'Review and import'],
  ['Import Result', 'View summary'],
]
const PAGE_SIZE = 8

export interface StudentImportOutcome {
  row: number
  name: string
  status: 'imported' | 'failed'
  message: string
}

export interface StudentRegistrationImport {
  readFile: (file: File) => Promise<ImportStudent[]>
  reviewRows: (rows: ImportStudent[]) => ReviewStudent[]
  importRows: (rows: ReviewStudent[], onProgress: (completed: number) => void) => Promise<StudentImportOutcome[]>
  onBusyChange: (busy: boolean) => void
}

export default function StudentImport({
  students,
  directoryReady,
  onBack,
  registration,
}: {
  students: Student[]
  directoryReady: boolean
  onBack: () => void
  registration?: StudentRegistrationImport
}) {
  const [upload, setUpload] = useState<{
    name: string
    time: Date
    rows: ImportStudent[]
  } | null>(null)
  const [stage, setStage] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<ReviewStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [onlySelected, setOnlySelected] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [reportMenu, setReportMenu] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const request = useRef(0)
  const active = useRef(false)
  const importing = useRef(false)
  const [outcomes, setOutcomes] = useState<StudentImportOutcome[]>([])
  const [importProgress, setImportProgress] = useState({ completed: 0, total: 0 })
  const onBusyChange = registration?.onBusyChange
  useEffect(() => {
    active.current = true
    return () => { active.current = false; request.current++ }
  }, [])
  useEffect(() => { onBusyChange?.(busy) }, [busy, onBusyChange])
  const reviewed = registration ? registration.reviewRows(upload?.rows ?? []) : validateStudents(upload?.rows ?? [], students)
  const columns = registration ? IMPORT_COLUMNS.slice(0, 4) : IMPORT_COLUMNS
  const counts = Object.fromEntries(
    Object.keys(statuses).map((status) => [
      status,
      reviewed.filter((row) => row.status === status).length,
    ]),
  ) as Record<ReviewStatus, number>
  const validSelected = reviewed.filter(
    (row) => row.status === 'valid' && selected.has(row.row),
  )
  const filtered = reviewed.filter(
    (row) =>
      (filter === 'all' || row.status === filter) &&
      (!onlySelected || selected.has(row.row)) &&
      `${row.name} ${row.registerNumber} ${row.rollNumber} ${row.email}`
        .toLowerCase()
        .includes(search.toLowerCase().trim()),
  )
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visible = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  )
  const selectable = visible.filter((row) => row.status === 'valid')
  const allSelected =
    selectable.length > 0 && selectable.every((row) => selected.has(row.row))

  async function choose(file: File) {
    const id = ++request.current
    setBusy(true)
    setError(null)
    try {
      const rows = await (registration ? registration.readFile(file) : readStudentFile(file))
      if (id !== request.current) return
      setUpload({ name: file.name, time: new Date(), rows })
      setStage(1)
      setOutcomes([])
      setPage(1)
      setFilter('all')
      setSearch('')
      setOnlySelected(false)
      setSelected(
        new Set(
          (registration ? registration.reviewRows(rows) : validateStudents(rows, students))
            .filter((row) => row.status === 'valid')
            .map((row) => row.row),
        ),
      )
    } catch (cause) {
      if (id === request.current)
        setError(
          cause instanceof Error
            ? cause.message
            : 'The file could not be read. Check its format and try again.',
        )
    } finally {
      if (id === request.current) setBusy(false)
    }
  }

  async function importSelected(rows: ReviewStudent[]) {
    if (!registration || busy || importing.current || !directoryReady || !rows.length) return
    importing.current = true
    setBusy(true)
    setError(null)
    setImportProgress({ completed: 0, total: rows.length })
    try {
      const result = await registration.importRows(rows, (completed) => {
        if (active.current) setImportProgress({ completed, total: rows.length })
      })
      if (!active.current) return
      setOutcomes((previous) => [...previous.filter((old) => !result.some((item) => item.row === old.row)), ...result].sort((a, b) => a.row - b.row))
      setStage(3)
    } catch (cause) {
      if (active.current) setError(cause instanceof Error ? cause.message : 'Registration could not be completed. Please try again.')
    } finally {
      importing.current = false
      if (active.current) setBusy(false)
    }
  }

  function toggle(row: number) {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(row)) next.delete(row)
      else next.add(row)
      return next
    })
  }
  function downloadReport(rows: ReviewStudent[]) {
    downloadCsv('student-validation-report.csv', [
      [
        ...columns,
        'file_row',
        'validation_status',
        'validation_message',
        ...(registration ? ['registration_result', 'registration_message'] : []),
      ],
      ...rows.map((row) => [
        row.name,
        row.registerNumber,
        row.rollNumber,
        row.email,
        ...(registration ? [] : [row.attendance]),
        row.row,
        row.status,
        row.message,
        ...(registration ? [outcomes.find((result) => result.row === row.row)?.status ?? '', outcomes.find((result) => result.row === row.row)?.message ?? ''] : []),
      ]),
    ])
  }
  function report() {
    downloadReport(reviewed)
  }
  function problemsReport() {
    downloadReport(reviewed.filter((row) => row.status !== 'valid' || outcomes.some((result) => result.row === row.row && result.status === 'failed')))
  }

  return (
    <section className="students-content" aria-label="Bulk student import">
      {!registration && <div className="students-breadcrumb">
        <button onClick={onBack}>Students</button>
        <ChevronRight />
        <span>Bulk Import</span>
        <ChevronRight />
        <span aria-current="page">
          {stage === 2
            ? 'Confirm Import'
            : stage === 1
              ? 'Validate & Preview'
              : 'Upload File'}
        </span>
      </div>}
      {!registration && <div className="students-title">
        <div>
          <h1>Bulk Student Import</h1>
          <p>
            {stage === 2
              ? 'Review your selection before importing student records.'
              : 'Validate the uploaded file and review student records before importing.'}
          </p>
        </div>
      </div>}
      <ol className="students-stepper" aria-label="Import progress">
        {steps.map(([label, description], index) => (
          <li
            key={label}
            className={index === stage ? 'is-current' : ''}
            aria-current={index === stage ? 'step' : undefined}
          >
            <span className="students-step-number">{index + 1}</span>
            <span>
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
          </li>
        ))}
      </ol>
      <input
        ref={fileInput}
        type="file"
        accept=".csv,.xlsx"
        aria-label="Choose student file"
        className="sr-only"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          if (file) void choose(file)
        }}
      />
      {error && (
        <div role="alert" className="students-alert error">
          <AlertCircle />
          <span>{error}</span>
        </div>
      )}
      {upload ? (
        <div className="students-file">
          <div className="students-file-icon">
            <FileSpreadsheet />
          </div>
          <div className="students-file-details">
            <strong>{upload.name}</strong>
            <p>
              Uploaded on{' '}
              {new Intl.DateTimeFormat(undefined, {
                dateStyle: 'medium',
                timeStyle: 'short',
              }).format(upload.time)}
              <span>·</span>
              {reviewed.length.toLocaleString()} records detected
            </p>
          </div>
          <button
            className="students-button"
            disabled={busy}
            onClick={() => fileInput.current?.click()}
          >
            <Upload />
            {busy && !importing.current ? 'Reading file…' : 'Replace File'}
          </button>
        </div>
      ) : (
        <div
          className={`students-dropzone ${dragging ? 'is-dragging' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            if (!busy && event.dataTransfer.files[0])
              void choose(event.dataTransfer.files[0])
          }}
        >
          <div className="students-upload-icon">
            <Upload />
          </div>
          <h2>Bring your student records together</h2>
          <p>
            Drag and drop your spreadsheet here, or choose a file to get
            started.
          </p>
          <button
            className="students-button primary"
            disabled={busy}
            onClick={() => fileInput.current?.click()}
          >
            <Upload />
            {busy ? 'Reading file…' : 'Choose File'}
          </button>
          <small>Excel (.xlsx) or CSV · Up to 5 MB · 1,000 records</small>
          <button
            className="students-text-button"
            onClick={() =>
              downloadCsv('student-import-template.csv', [columns])
            }
          >
            <Download />
            Download CSV template
          </button>
        </div>
      )}
      {!upload && (
        <div className="students-format">
          <Info />
          <div>
            <strong>A little preparation goes a long way.</strong>
            <p>
              {registration ? 'Include name and register_number. Email is optional; university_roll_number is required after the first semester. Attendance is managed separately. ' : 'Include name, register_number, university_roll_number, and email. Attendance is optional (0–100). '}
              Format identifiers as text to preserve leading zeros. Excel reads the first sheet.
            </p>
          </div>
        </div>
      )}
      {upload && (
        <>
          {stage !== 3 && <div className="students-stats">
            {(Object.keys(statuses) as ReviewStatus[]).map((status) => {
              const { title, description, Icon } = statuses[status]
              return (
                <button
                  key={status}
                  className={`students-stat ${status} ${filter === status ? 'is-selected' : ''}`}
                  onClick={() => {
                    setFilter(filter === status ? 'all' : status)
                    setPage(1)
                  }}
                  aria-pressed={filter === status}
                >
                  <span className="students-stat-icon">
                    <Icon />
                  </span>
                  <span>
                    <strong>{counts[status]}</strong>
                    <b>{title}</b>
                    <small>{description}</small>
                  </span>
                </button>
              )
            })}
          </div>}
          {!directoryReady && (
            <div role="status" className="students-alert">
              <Info />
              <span>
                Student records must finish loading before existing student
                numbers can be checked. You can still review file errors.
              </span>
            </div>
          )}
          {stage === 1 ? (
            <>
              <div className="students-toolbar">
                <div
                  className="students-tabs"
                  role="group"
                  aria-label="Validation status"
                >
                  <button
                    className={filter === 'all' ? 'active' : ''}
                    onClick={() => {
                      setFilter('all')
                      setPage(1)
                    }}
                  >
                    All Records ({reviewed.length})
                  </button>
                  {(Object.keys(statuses) as ReviewStatus[]).map((status) => {
                    const { Icon, label } = statuses[status]
                    return (
                      <button
                        key={status}
                        className={filter === status ? 'active' : ''}
                        onClick={() => {
                          setFilter(status)
                          setPage(1)
                        }}
                      >
                        <Icon className={status} />
                        {label} ({counts[status]})
                      </button>
                    )
                  })}
                </div>
                <div className="students-table-actions">
                  <label className="students-search">
                    <Search />
                    <input
                      type="search"
                      aria-label="Search import records"
                      placeholder="Search name, register no, roll no…"
                      value={search}
                      onChange={(event) => {
                        setSearch(event.target.value)
                        setPage(1)
                      }}
                    />
                  </label>
                  <button
                    className={`students-button ${showFilters ? 'is-active' : ''}`}
                    aria-expanded={showFilters}
                    aria-controls="student-import-filters"
                    onClick={() => setShowFilters(!showFilters)}
                  >
                    <Filter />
                    Filters{onlySelected ? ' (1)' : ''}
                  </button>
                </div>
              </div>
              {showFilters && (
                <div
                  id="student-import-filters"
                  className="students-filter-panel"
                >
                  <label>
                    <input
                      type="checkbox"
                      checked={onlySelected}
                      onChange={(event) => {
                        setOnlySelected(event.target.checked)
                        setPage(1)
                      }}
                    />
                    Show selected records only
                  </label>
                  <button
                    className="students-text-button"
                    onClick={() => {
                      setOnlySelected(false)
                      setFilter('all')
                      setSearch('')
                      setPage(1)
                    }}
                  >
                    Clear filters
                  </button>
                </div>
              )}
              <div className="students-table-scroll">
                <table className="students-table">
                  <caption className="sr-only">
                    Student file validation preview
                  </caption>
                  <thead>
                    <tr>
                      <th className="selection">
                        <input
                          type="checkbox"
                          aria-label="Select all valid records on this page"
                          disabled={!selectable.length || busy}
                          checked={allSelected}
                          ref={(element) => {
                            if (element)
                              element.indeterminate =
                                !allSelected &&
                                selectable.some((row) => selected.has(row.row))
                          }}
                          onChange={() =>
                            setSelected((previous) => {
                              const next = new Set(previous)
                              selectable.forEach((row) => {
                                if (allSelected) next.delete(row.row)
                                else next.add(row.row)
                              })
                              return next
                            })
                          }
                        />
                      </th>
                      <th>#</th>
                      <th>Name</th>
                      <th>Register Number</th>
                      <th>University Roll No</th>
                      <th>Email</th>
                      {!registration && <th>Attendance %</th>}
                      <th>Status</th>
                      <th>Validation Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((row) => {
                      const { Icon, label } = statuses[row.status]
                      return (
                        <tr key={row.row} className={row.status}>
                          <td className="selection">
                            <input
                              type="checkbox"
                              aria-label={`Select ${row.name || `row ${row.row}`}`}
                              checked={
                                row.status === 'valid' && selected.has(row.row)
                              }
                              disabled={row.status !== 'valid' || busy}
                              onChange={() => toggle(row.row)}
                            />
                          </td>
                          <td>{row.row - 1}</td>
                          <td className="student-name">{row.name || '—'}</td>
                          <td>{row.registerNumber || '—'}</td>
                          <td>{row.rollNumber || '—'}</td>
                          <td>{row.email || '—'}</td>
                          {!registration && <td>{row.attendance ? `${row.attendance}%` : '—'}</td>}
                          <td>
                            <span className={`students-status ${row.status}`}>
                              <Icon />
                              {label}
                            </span>
                          </td>
                          <td className="validation-message">{row.message}</td>
                        </tr>
                      )
                    })}
                    {!visible.length && (
                      <tr>
                        <td colSpan={registration ? 8 : 9} className="students-empty">
                          No records match these filters.
                          <button
                            className="students-text-button"
                            onClick={() => {
                              setSearch('')
                              setFilter('all')
                              setOnlySelected(false)
                              setPage(1)
                            }}
                          >
                            Clear filters
                          </button>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="students-pagination">
                <p>
                  Showing{' '}
                  {filtered.length ? (currentPage - 1) * PAGE_SIZE + 1 : 0}–
                  {Math.min(currentPage * PAGE_SIZE, filtered.length)} of{' '}
                  {filtered.length} records
                </p>
                <div>
                  <button
                    className="students-page"
                    aria-label="Previous page"
                    disabled={currentPage === 1}
                    onClick={() => setPage(currentPage - 1)}
                  >
                    <ChevronLeft />
                  </button>
                  {Array.from(
                    { length: Math.min(5, totalPages) },
                    (_, index) =>
                      Math.min(
                        Math.max(1, currentPage - 2),
                        Math.max(1, totalPages - 4),
                      ) + index,
                  ).map((number) => (
                    <button
                      className={`students-page ${currentPage === number ? 'active' : ''}`}
                      aria-label={`Page ${number}`}
                      aria-current={currentPage === number ? 'page' : undefined}
                      key={number}
                      onClick={() => setPage(number)}
                    >
                      {number}
                    </button>
                  ))}
                  <button
                    className="students-page"
                    aria-label="Next page"
                    disabled={currentPage === totalPages}
                    onClick={() => setPage(currentPage + 1)}
                  >
                    <ChevronRight />
                  </button>
                </div>
              </div>
            </>
          ) : stage === 3 ? (
            <section className="students-confirm" aria-label="Registration results">
              <div className="students-upload-icon"><CheckCircle2 /></div>
              <h2>Registration results</h2>
              <p role="status">Registered: {outcomes.filter((item) => item.status === 'imported').length} · Failed: {outcomes.filter((item) => item.status === 'failed').length} · Skipped: {reviewed.length - outcomes.length}</p>
              <div className="students-table-scroll"><table className="students-table">
                <caption className="sr-only">Bulk registration results</caption>
                <thead><tr><th>File row</th><th>Student</th><th>Result</th><th>Message</th></tr></thead>
                <tbody>{outcomes.map((item) => <tr key={item.row}><td>{item.row}</td><td className="student-name">{item.name}</td><td><span className={`students-status ${item.status === 'imported' ? 'valid' : 'invalid'}`}>{item.status === 'imported' ? 'Registered' : 'Failed'}</span></td><td className="validation-message">{item.message}</td></tr>)}</tbody>
              </table></div>
              <p>Student accounts still require signup and approval before students can sign in.</p>
              {outcomes.some((item) => item.status === 'failed') && <button className="students-button" disabled={busy || !directoryReady || !reviewed.some((row) => row.status === 'valid' && outcomes.some((item) => item.row === row.row && item.status === 'failed'))} onClick={() => void importSelected(reviewed.filter((row) => row.status === 'valid' && outcomes.some((item) => item.row === row.row && item.status === 'failed')))}>{busy ? 'Registering students…' : 'Retry failed registrations'}</button>}
            </section>
          ) : (
            <section className="students-confirm">
              <div className="students-upload-icon">
                <FileSpreadsheet />
              </div>
              <h2>{validSelected.length} records selected for import</h2>
              <p>
                Only selected records that passed file checks are included.
                Duplicates, invalid records, and conflicts are excluded.
              </p>
              <div className="students-alert">
                <Info />
                <span>
                  {registration ? 'The selected students will be added to this section. Account matching, semester requirements, and permissions are checked again when each student is registered.' : <>Saving bulk student records is not available yet. Download the
                  validation report to keep your review. No student records have
                  been created or changed.</>}
                </span>
              </div>
              <button className="students-button primary" disabled={!registration || busy || !directoryReady || !validSelected.length} onClick={() => void importSelected(validSelected)}>
                {registration ? busy ? `Registering students… ${importProgress.completed}/${importProgress.total}` : `Register ${validSelected.length} student${validSelected.length === 1 ? '' : 's'}` : 'Import unavailable'}
              </button>
            </section>
          )}
          <div className="students-footer">
            <div className="students-report">
              <button
                className="students-button students-report-main"
                onClick={report}
              >
                <Download />
                Download Validation Report
              </button>
              <button
                className="students-button students-report-toggle"
                aria-label="More download options"
                aria-haspopup="menu"
                aria-expanded={reportMenu}
                onClick={() => setReportMenu((open) => !open)}
              >
                <ChevronDown />
              </button>
              {reportMenu && (
                <>
                  <button
                    className="students-report-scrim"
                    aria-label="Close download options"
                    onClick={() => setReportMenu(false)}
                  />
                  <div className="students-report-menu" role="menu">
                    <button
                      role="menuitem"
                      onClick={() => {
                        report()
                        setReportMenu(false)
                      }}
                    >
                      All records (.csv)
                    </button>
                    <button
                      role="menuitem"
                      onClick={() => {
                        problemsReport()
                        setReportMenu(false)
                      }}
                    >
                      Problems only (.csv)
                    </button>
                  </div>
                </>
              )}
            </div>
            <div>
              <button
                className="students-button"
                disabled={busy}
                onClick={() => {
                  if (stage === 3) onBack()
                  else if (stage === 2) setStage(1)
                  else {
                    setUpload(null)
                    setStage(0)
                    setSelected(new Set())
                  }
                }}
              >
                {stage === 3 ? 'View Students' : stage === 2 ? 'Back to Preview' : 'Back'}
              </button>
              {stage !== 3 && <button
                className="students-button primary"
                disabled={
                  busy ||
                  !directoryReady ||
                  !validSelected.length ||
                  stage !== 1
                }
                onClick={() => setStage(2)}
              >
                Continue to Import
                <ArrowRight />
              </button>}
            </div>
          </div>
          <p className="students-review-note">
            {registration ? 'Validation checks this file against the selected section roster. Final identity and semester checks take place during registration.' : 'Validation checks this file and your institution’s student numbers. Final account and identity checks will be required before any import.'}
          </p>
        </>
      )}
    </section>
  )
}
