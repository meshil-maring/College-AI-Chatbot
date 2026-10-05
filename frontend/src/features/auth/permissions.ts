/** Presentation helpers for server-resolved permissions; never an API security boundary. */
export function hasPermission(
  granted: readonly string[] | undefined,
  required: string,
): boolean {
  if (granted === undefined) return false
  if (granted.includes(required) || granted.includes('*')) return true
  const separator = required.indexOf('.')
  return separator > 0 && granted.includes(`${required.slice(0, separator)}.*`)
}
