/**
 * Phase 6.16 — Small display formatters for the student experience.
 *
 * Pure formatting only. No calculation is performed here and no value is
 * invented: a percentage shown in the UI is ALWAYS the number the backend
 * computed (the authoritative attendance rule lives server-side).
 */

import { NOT_PROVIDED } from './SectionState.tsx'

/** Render an ISO date/time as a readable local date, or the em dash. */
export function formatDate(value: string | null | undefined): string {
  if (value === null || value === undefined) return NOT_PROVIDED
  const text = String(value).trim()
  if (text === '') return NOT_PROVIDED
  const parsed = new Date(text)
  if (Number.isNaN(parsed.getTime())) return text
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/** Render a backend-provided percentage, or the em dash when it is null. */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_PROVIDED
  return `${value}%`
}

/** Render a numeric marks value, or the em dash. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_PROVIDED
  return String(value)
}

/**
 * Render a machine value (e.g. `cash`, `notice`, `under_review`) as a readable
 * label. The vocabulary is NOT translated into new terms — only underscores and
 * surrounding whitespace are normalised, so the UI can never invent a status.
 */
export function formatLabel(value: string | null | undefined): string {
  if (value === null || value === undefined) return NOT_PROVIDED
  const text = String(value).trim().replace(/[_-]+/g, ' ')
  if (text === '') return NOT_PROVIDED
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Marks such as "42/50"; both parts may be absent. */
export function formatScore(
  scored: number | null | undefined,
  max: number | null | undefined,
): string {
  if (scored === null || scored === undefined) return NOT_PROVIDED
  const scoredText = String(scored)
  if (max === null || max === undefined) return scoredText
  return `${scoredText}/${max}`
}
