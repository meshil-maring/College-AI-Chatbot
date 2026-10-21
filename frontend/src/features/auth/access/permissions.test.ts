import { describe, expect, it } from 'vitest'
import { hasPermission } from './permissions.ts'

describe('hasPermission', () => {
  it('matches exact and resource-wildcard grants', () => {
    expect(hasPermission(['students.read'], 'students.read')).toBe(true)
    expect(hasPermission(['students.*'], 'students.read')).toBe(true)
    expect(hasPermission(['*'], 'results.manage')).toBe(true)
  })

  it('does not infer privileges from partial or absent grants', () => {
    expect(hasPermission(['students.read'], 'students.delete')).toBe(false)
    expect(hasPermission(['student.*'], 'students.read')).toBe(false)
    expect(hasPermission(undefined, 'students.read')).toBe(false)
  })
})
