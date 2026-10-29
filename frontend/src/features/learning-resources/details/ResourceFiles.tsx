import { FileText } from 'lucide-react'
import type { ResourceFile } from '../../../types/learningResources.ts'
import { IndexBadge } from '../ResourceBadges.tsx'
import { fileSize } from '../resourcePresentation.ts'

export default function ResourceFiles({
  files,
  disabled = false,
  onReplace,
  onRetry,
}: {
  files: ResourceFile[]
  disabled?: boolean
  onReplace?: (documentId: string) => void
  onRetry?: (versionId: string) => void
}) {
  return (
    <section className="lr-files" aria-label="Resource files">
      <h3>
        Files <span className="lr-help">({files.length})</span>
      </h3>
      {!files.length ? (
        <p className="lr-help">No files attached yet. Add a file before submitting for review.</p>
      ) : (
        <ul>
          {files.map((file) => (
            <li key={file.document_version_id}>
              <FileText size={20} aria-hidden="true" />
              <div className="lr-file-info">
                <strong>{file.original_filename}</strong>
                <p className="lr-help">
                  Version {file.version_number} · {file.file_type.toUpperCase()} · {fileSize(file.file_size_bytes)}
                </p>
                <IndexBadge status={file.indexing_status} />
              </div>
              {(onReplace || (onRetry && file.indexing_status === 'failed')) && (
                <div className="lr-file-actions">
                  {onReplace && (
                    <button
                      type="button"
                      className="lr-secondary"
                      disabled={disabled}
                      aria-label={`Replace ${file.original_filename}`}
                      onClick={() => onReplace(file.document_id)}
                    >
                      Replace file
                    </button>
                  )}
                  {onRetry && file.indexing_status === 'failed' && (
                    <button
                      type="button"
                      className="lr-secondary"
                      disabled={disabled}
                      aria-label={`Retry indexing ${file.original_filename}`}
                      onClick={() => onRetry(file.document_version_id)}
                    >
                      Retry indexing
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
