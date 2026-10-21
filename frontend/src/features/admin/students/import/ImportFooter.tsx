import { ArrowRight, ChevronDown, Download } from 'lucide-react'
import type { StudentImportModel } from './useStudentImport.ts'
export function ImportFooter({ model }: { model: StudentImportModel }) {
  const {
    directoryReady,
    onBack,
    registration,
    setUpload,
    stage,
    setStage,
    busy,
    setSelected,
    reportMenu,
    setReportMenu,
    validSelected,
    report,
    problemsReport,
  } = model
  return (
    <div className="students-footer">
      <div className="students-report">
        <button className="students-button students-report-main" onClick={report}>
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
          disabled={busy || registration?.resultsBusy}
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
        {stage !== 3 && (
          <button
            className="students-button primary"
            disabled={busy || !directoryReady || !validSelected.length || stage !== 1}
            onClick={() => setStage(2)}
          >
            Continue to Import
            <ArrowRight />
          </button>
        )}
      </div>
    </div>
  )
}
