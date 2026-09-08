/**
 * Phase 5.5 — Usage / model metadata badge.
 *
 * Compact display of backend-provided token counts and model identifier.
 *   - Input:  N tokens
 *   - Output: M tokens
 *   - Model:  <model_used>
 *
 * The frontend never calculates billing/cost and never invents token counts.
 * When usage is null, no fake values are shown. When model_used is null, the
 * model line is omitted.
 */

import type { ChatUsage } from '../../types/chat.ts'

export default function UsageBadge({
  usage,
  modelUsed,
}: {
  usage: ChatUsage | null
  modelUsed: string | null
}) {
  const input = usage?.input_tokens
  const output = usage?.output_tokens
  const hasUsage =
    (typeof input === 'number' && Number.isFinite(input)) ||
    (typeof output === 'number' && Number.isFinite(output))

  if (!hasUsage && !modelUsed) {
    return null
  }

  const parts: string[] = []
  if (typeof input === 'number' && Number.isFinite(input)) {
    parts.push(`Input: ${input} tokens`)
  }
  if (typeof output === 'number' && Number.isFinite(output)) {
    parts.push(`Output: ${output} tokens`)
  }

  return (
    <p className="text-[11px] text-slate-500" aria-label="Response metadata">
      {parts.length > 0 ? <span>{parts.join(' · ')}</span> : null}
      {parts.length > 0 && modelUsed ? ' · ' : null}
      {modelUsed ? `Model: ${modelUsed}` : null}
    </p>
  )
}