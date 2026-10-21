import './__tests__/CrossRoleIntegration.support.tsx'
import { ROLES, setIdentity } from './__tests__/CrossRoleIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import App from './App.tsx'
describe('no token exposure', () => {
  it('never renders the access token or internal identifiers for any role', () => {
    const { rerender } = render(<App />)

    for (const [role, user] of ROLES) {
      setIdentity(user, role)
      rerender(<App />)
      expect(document.body.innerHTML, role).not.toContain('cross-role-token')
      expect(screen.queryByText('cross-role-token')).not.toBeInTheDocument()
      expect(document.body.innerHTML, role).not.toContain(user.auth_user_id)
    }
  })
})
