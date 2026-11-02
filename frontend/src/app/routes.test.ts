import { describe, expect, it } from 'vitest'
import { resolveAppRoute } from './routes.ts'

describe('public student setup route', () => {
  it('resolves without requiring the invitation token in the path', () => {
    expect(resolveAppRoute('/student-setup')).toEqual({ kind: 'student-setup' })
    expect(resolveAppRoute('/student-setup/')).toEqual({ kind: 'student-setup' })
  })
})
