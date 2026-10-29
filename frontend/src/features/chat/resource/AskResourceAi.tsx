import { useEffect, useRef, useState } from 'react'
import { Bot } from 'lucide-react'
import { getResourceChatContext, ResourceApiError } from '../../../services/knowledge/resources.ts'
import type { ResourceChatContext } from '../../../types/chat.ts'

export default function AskResourceAi({
  context,
  sourceId,
  disabled,
  isCurrent,
  onReady,
}: {
  context: { accessToken: string; canAsk: boolean }
  sourceId: string
  disabled: boolean
  isCurrent: () => boolean
  onReady: (context: ResourceChatContext) => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pending = useRef(false)
  const controller = useRef<AbortController | null>(null)
  useEffect(
    () => () => {
      controller.current?.abort()
    },
    [],
  )
  async function open() {
    if (pending.current) return
    pending.current = true
    setBusy(true)
    setError(null)
    const request = new AbortController()
    controller.current = request
    try {
      const resource = await getResourceChatContext(context.accessToken, sourceId, request.signal)
      if (resource.knowledge_source_id !== sourceId || !resource.available) throw new Error('Resource context mismatch')
      if (!request.signal.aborted && isCurrent()) onReady(resource)
    } catch (failure) {
      if (request.signal.aborted || !isCurrent()) return
      setError(
        failure instanceof ResourceApiError && [403, 404].includes(failure.status)
          ? 'This resource is unavailable to AI. Its publication, audience or indexing may have changed.'
          : 'Resource access could not be confirmed. Please try again.',
      )
    } finally {
      if (!request.signal.aborted && isCurrent()) {
        pending.current = false
        setBusy(false)
      }
    }
  }
  if (!context.canAsk) return null
  return (
    <div className="mt-3 space-y-2 border-t border-line pt-3">
      <p className="text-xs text-muted">
        Start a new conversation whose answers and follow-ups use only this resource.
      </p>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <button type="button" className="ui-primary" disabled={disabled || busy} onClick={() => void open()}>
        <Bot aria-hidden="true" size={16} />
        {busy ? 'Checking resource…' : 'Ask AI'}
      </button>
    </div>
  )
}
