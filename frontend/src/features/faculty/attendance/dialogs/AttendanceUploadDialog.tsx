import { correctFacultyAttendanceImportRow } from '../../../../services/faculty/facultyAttendanceApi.ts'
import { Modal, NoAssignmentWorkflow } from './AttendanceDialog.tsx'
import { Glyph, Stepper } from '../shared/AttendanceWorkspaceUi.tsx'
import { ReviewImportStage, UploadFileStage, ValidationResultsStage } from '../upload/UploadAttendanceStages.tsx'
import type { FacultyAttendanceWorkspaceModel } from '../state/useAttendanceWorkspace.ts'
export function AttendanceUploadDialog({ model }: { model: FacultyAttendanceWorkspaceModel }) {
  const {
    accessToken,
    onNavigateAssignments,
    review,
    setReview,
    pendingFile,
    setPendingFile,
    uploadOpen,
    setUploadOpen,
    uploadStep,
    setUploadStep,
    uploadSuccess,
    setUploadSuccess,
    aiConfirmationFile,
    setAiConfirmationFile,
    dragging,
    setDragging,
    saving,
    setSaving,
    error,
    setError,
    assignments,
    canManage,
    onFileSelected,
    processFile,
    commit,
    downloadValidationErrors,
  } = model
  return (
    <>
      {uploadOpen ? (
        <Modal
          title={uploadSuccess ? 'Import Complete' : 'Upload Attendance'}
          onClose={() => setUploadOpen(false)}
          wide
        >
          <Stepper active={uploadStep} success={uploadSuccess} />
          {uploadSuccess ? (
            <div className="py-10 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500 text-[#06131f]">
                <Glyph name="check" size={30} />
              </div>
              <h2 className="mt-4 text-xl font-bold text-white">Attendance Imported Successfully</h2>
              <p className="mt-2 text-sm text-slate-400">
                {review?.summary.total_rows ?? review?.rows.length ?? 0} records processed. Invalid or conflicting
                records remain excluded.
              </p>
              <button
                type="button"
                onClick={() => {
                  setUploadSuccess(false)
                  setReview(null)
                  setPendingFile(null)
                  setAiConfirmationFile(null)
                  setUploadStep(1)
                }}
                className="mt-6 rounded-lg bg-[#ffc72c] px-4 py-2 text-sm font-bold text-[#101820]"
              >
                Import Another File
              </button>
            </div>
          ) : assignments.length === 0 || (!canManage && !review) ? (
            <NoAssignmentWorkflow
              action="upload attendance"
              onNavigateAssignments={onNavigateAssignments}
              onClose={() => setUploadOpen(false)}
            />
          ) : uploadStep === 1 ? (
            <UploadFileStage
              dragging={dragging}
              pendingFile={pendingFile}
              aiConfirmationFile={aiConfirmationFile}
              saving={saving}
              error={error}
              onDraggingChange={setDragging}
              onFileSelected={onFileSelected}
              onRemoveFile={() => {
                setPendingFile(null)
                setAiConfirmationFile(null)
                setError(null)
              }}
              onCancelAi={() => {
                setAiConfirmationFile(null)
                setError(null)
              }}
              onProcess={(file, aiConfirmed) => void processFile(file, aiConfirmed)}
            />
          ) : uploadStep === 2 && saving ? (
            <div role="status" className="py-14 text-center">
              <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[#ffc72c] border-t-transparent" />
              <p className="mt-4 text-sm text-slate-300">Validating your file…</p>
            </div>
          ) : uploadStep === 2 ? (
            <ValidationResultsStage
              review={review}
              onBack={() => {
                setUploadStep(1)
                setReview(null)
              }}
              onContinue={() => setUploadStep(3)}
              onDownloadErrors={downloadValidationErrors}
            />
          ) : (
            <ReviewImportStage
              review={review}
              saving={saving}
              readOnly={!canManage || review?.status === 'IMPORTED'}
              onCorrect={
                canManage && review?.status !== 'IMPORTED'
                  ? (row, data) => {
                      if (!review) return
                      setSaving(true)
                      correctFacultyAttendanceImportRow(accessToken, review.import_id, row, data)
                        .then(setReview)
                        .catch((cause: unknown) =>
                          setError(cause instanceof Error ? cause.message : 'Correction failed'),
                        )
                        .finally(() => setSaving(false))
                    }
                  : undefined
              }
              onBack={() => setUploadStep(2)}
              onCommit={() => void commit()}
              error={error}
            />
          )}
        </Modal>
      ) : null}
    </>
  )
}
