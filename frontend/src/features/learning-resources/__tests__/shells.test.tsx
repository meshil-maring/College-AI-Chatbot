import './mockSetup.ts'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { auth } from './mockSetup.ts'
import { user as identity } from './fixtures.ts'
import AdminShell from '../../admin/AdminShell.tsx'
import FacultyShell from '../../faculty/workspace/FacultyShell.tsx'
import StaffShell from '../../staff/StaffShell.tsx'

describe('shared Learning Resources workspace composition', () => {
  it.each([
    ['admin', AdminShell],
    ['faculty', FacultyShell],
    ['staff', StaffShell],
  ] as const)('mounts the shared page from the %s navigation', async (role, Shell) => {
    auth.user = identity(role)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <Shell />
      </QueryClientProvider>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Learning Resources', exact: true }))
    expect(await screen.findByRole('button', { name: 'View Published handbook' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { name: 'Learning Resources', level: 1 })).toHaveLength(1)
  })
})
