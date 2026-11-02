import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import StudentWorkspaceNavigation from './StudentWorkspaceNavigation.tsx'

describe('student workspace navigation', () => {
  it('lists student destinations in workspace order and selects the requested page', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(<StudentWorkspaceNavigation currentPage="register" onNavigate={onNavigate} />)

    const navigation = screen.getByRole('list', { name: 'Students pages' })
    const items = within(navigation).getAllByRole('button')
    expect(items.map((item) => item.textContent)).toEqual([
      'All Students',
      'Add Student',
      'Bulk Import',
      'Registration Requests',
    ])
    expect(within(navigation).getByRole('button', { name: 'Add Student' })).toHaveAttribute('aria-current', 'page')

    await user.click(within(navigation).getByRole('button', { name: 'Bulk Import' }))
    expect(onNavigate).toHaveBeenCalledWith('bulk')
    expect(navigation).toBeInTheDocument()
  })
})
