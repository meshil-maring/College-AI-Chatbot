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
  if (typeof value !== 'number' || !Number.isFinite(value)) return NOT_PROVIDED
  return `${value}%`
}

/** Render a numeric marks value, or the em dash. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return NOT_PROVIDED
  if (typeof value !== 'number' || !Number.isFinite(value)) return NOT_PROVIDED
  return String(value)
}

/**
 * Render a machine value (e.g. `cash`, `notice`, `under_review`) as a readable
 * label. The vocabulary is NOT translated into new terms — only underscores and
 * surrounding whitespace are normalised, so the UI can never invent a status.
 * Non-string payloads (objects, numbers, booleans) render as the em dash so
 * the UI can never show `[object Object]`, `undefined`, `null`, or `NaN`.
 */
export function formatLabel(value: unknown): string {
  if (typeof value !== 'string') return NOT_PROVIDED
  const text = value.trim().replace(/[_-]+/g, ' ')
  if (text === '') return NOT_PROVIDED
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Render a command-supplied string safely (never undefined/null/NaN/[object Object]). */
export function formatText(value: unknown): string {
  if (value === null || value === undefined) return NOT_PROVIDED
  if (typeof value === 'string') {
    const text = value.trim()
    return text === '' ? NOT_PROVIDED : text
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    if (typeof value === 'number' && !Number.isFinite(value)) return NOT_PROVIDED
    return String(value)
  }
  return NOT_PROVIDED
}

/** True when a value is a finite number safe to render as a measurement. */
export function isDisplayableNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

/** Marks such as "42/50"; both parts may be absent. */
export function formatScore(
  scored: number | null | undefined,
  max: number | null | undefined,
): string {
  if (typeof scored !== 'number' || !Number.isFinite(scored)) return NOT_PROVIDED
  if (typeof max !== 'number' || !Number.isFinite(max)) return String(scored)
  return `${scored}/${max}`
}
