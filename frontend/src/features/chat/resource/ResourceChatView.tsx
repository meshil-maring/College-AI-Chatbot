import ChatShell from '../ChatShell.tsx'
import type { ResourceChatContext } from '../../../types/chat.ts'

export default function ResourceChatView({ resource, onBack }: { resource: ResourceChatContext; onBack: () => void }) {
  return (
    <section aria-label="Resource AI Assistant">
      <button
        type="button"
        className="mb-3 rounded-lg border border-control px-3 py-2 text-sm text-content"
        onClick={onBack}
      >
        Back to Learning Resources
      </button>
      <ChatShell initialResource={resource} />
    </section>
  )
}
