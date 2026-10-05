import { describe, expect, it } from 'vitest'
import { resolveAppRoute } from '../../App.tsx'
import { extractSuperAdminInviteToken } from './SuperAdminRegisterEntryPage.tsx'

const TOKEN = 'a'.repeat(64)

describe('super admin registration entry', () => {
  it('extracts the token from a link or a bare code', () => {
    expect(extractSuperAdminInviteToken(`https://x.test/super-admin-invite/${TOKEN}`)).toBe(TOKEN)
    expect(extractSuperAdminInviteToken(`  ${TOKEN} `)).toBe(TOKEN)
    expect(extractSuperAdminInviteToken('short')).toBeNull()
  })

  it('resolves the registration routes', () => {
    expect(resolveAppRoute('/register/super-admin')).toEqual({ kind: 'super-admin-register' })
    expect(resolveAppRoute(`/super-admin-invite/${TOKEN}`)).toEqual({
      kind: 'super-admin-invitation',
      token: TOKEN,
    })
  })
})
