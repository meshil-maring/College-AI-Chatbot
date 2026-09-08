/**
 * Phase 5.5 — Source / citation card.
 *
 * Renders one backend-provided StructuredSource. The frontend never generates
 * or rewrites citations: it only displays the backend-provided values.
 *   - source_title   (when available)
 *   - section        (when available)
 *   - quote          (verbatim, never modified)
 *   - relevance_score (when available)
 */

import type { StructuredSource } from '../../types/chat.ts'

function formatRelevance(score: number | null | undefined): string | null {
  if (score === null || score === undefined) {
    return null
  }
  const percent = Math.round(score * 100)
  return `${percent}%`
}

export default function SourceCard({ source }: { source: StructuredSource }) {
  const relevance = formatRelevance(source.relevance_score)
  const title = source.source_title?.trim() || 'Source'
  const section = source.section?.trim()

  return (
    <article className="rounded-lg border border-slate-600 bg-slate-800/80 px-3 py-2">
      <header className="flex items-start justify-between gap-2">
        <h4 className="text-xs font-semibold text-slate-200">
          {title}
          {section ? (
            <span className="text-slate-400"> · {section}</span>
          ) : null}
        </h4>
        {relevance !== null ? (
          <span className="shrink-0 text-[11px] text-slate-400">
            Relevance {relevance}
          </span>
        ) : null}
      </header>
      <blockquote className="mt-1 text-xs italic text-slate-300">
        “{source.quote}”
      </blockquote>
    </article>
  )
}