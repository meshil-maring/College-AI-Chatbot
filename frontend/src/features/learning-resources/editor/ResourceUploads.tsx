import { useEffect, useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { retryResourceIndex, uploadResourceFile } from '../../../services/knowledge/resources.ts'
import type { ResourceRevision } from '../../../types/learningResources.ts'
import type { ResourceContext } from '../data/resourceIdentity.ts'
import type { ResourceActions } from '../data/useResourceActions.ts'
import ResourceFiles from '../details/ResourceFiles.tsx'

export default function ResourceUploads({
  context,
  revision,
  actions,
  disabled,
  onDirty,
}: {
  context: ResourceContext
  revision: ResourceRevision
  actions: ResourceActions
  disabled: boolean
  onDirty: (dirty: boolean) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [target, setTarget] = useState('')
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const busy = disabled || actions.saving || actions.blocked
  const documentId = target || (!context.canUpload ? (revision.documents[0]?.document_id ?? '') : '')
  const allowed = documentId ? context.canReplace : context.canUpload
  function clearFile() {
    setFile(null)
    if (input.current) input.current.value = ''
  }
  useEffect(() => {
    onDirty(file !== null)
  }, [file, onDirty])
  useEffect(() => {
    if (actions.indexingFailed) clearFile()
  }, [actions.indexingFailed])
  async function upload() {
    if (!file || busy || !allowed) return
    if (!/\.(pdf|docx|txt)$/i.test(file.name) || file.size === 0) {
      setError('Choose a nonempty PDF, DOCX or TXT file.')
      return
    }
    setError('')
    const saved = await actions.run(
      () => uploadResourceFile(context.accessToken, revision, file, documentId || undefined),
      'upload',
    )
    if (saved) clearFile()
  }
  return (
    <section className="lr-upload-section">
      <ResourceFiles
        files={revision.documents}
        disabled={busy || Boolean(file)}
        onReplace={
          context.canReplace
            ? (id) => {
                setTarget(id)
                input.current?.focus()
              }
            : undefined
        }
        onRetry={(id) => {
          if (!busy && !file) void actions.run(() => retryResourceIndex(context.accessToken, revision, id), 'retry')
        }}
      />
      {(context.canUpload || (context.canReplace && revision.documents.length > 0)) && (
        <div className="lr-upload-box">
          <h3>
            <Upload size={18} aria-hidden="true" />
            Attach a file
          </h3>
          <p className="lr-help">PDF, DOCX or TXT. Files stay private while the draft is indexed and reviewed.</p>
          <label htmlFor="resource-file-target">File destination</label>
          <select
            id="resource-file-target"
            value={documentId}
            disabled={busy}
            onChange={(event) => setTarget(event.target.value)}
          >
            {context.canUpload && <option value="">Add a new file</option>}
            {context.canReplace &&
              revision.documents.map((item) => (
                <option key={item.document_id} value={item.document_id}>
                  Replace {item.original_filename}
                </option>
              ))}
          </select>
          <label htmlFor="resource-file">Choose file</label>
          <input
            ref={input}
            id="resource-file"
            type="file"
            accept=".pdf,.docx,.txt"
            disabled={busy}
            aria-describedby="resource-file-help"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError('')
            }}
          />
          <p id="resource-file-help" className="lr-help">
            A replacement affects the live resource only after admin publication.
          </p>
          {error && (
            <p role="alert" className="lr-field-error">
              {error}
            </p>
          )}
          {file && (
            <button type="button" className="lr-secondary" disabled={actions.saving} onClick={clearFile}>
              Clear file selection
            </button>
          )}
          <button
            type="button"
            className="lr-secondary"
            disabled={busy || !file || !allowed}
            onClick={() => void upload()}
          >
            {actions.saving && actions.activity === 'upload' ? 'Uploading and indexing…' : 'Upload and index'}
          </button>
        </div>
      )}
    </section>
  )
}
