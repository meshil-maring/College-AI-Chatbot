import type { ResourceChatContext } from '../../types/chat.ts'

export default function ResourceChatBanner({ resource }: { resource: ResourceChatContext | null }) {
  if (!resource) return null
  return (
    <section aria-label="Resource conversation scope" className="border-b border-line bg-raised px-4 py-3">
      <h2 className="text-sm font-semibold text-content break-words">
        {resource.available ? `Asking about: ${resource.title ?? 'Selected resource'}` : 'Resource unavailable'}
      </h2>
      <p className="mt-1 text-xs text-muted">
        {resource.available
          ? 'Answers and follow-up questions use only this resource.'
          : 'Access changed. Return to Learning Resources to choose an available resource.'}
      </p>
    </section>
  )
}
