import './__tests__/AcademicSetup.support.ts'
import { auth, catalogue, department } from './__tests__/AcademicSetup.support.ts'
import * as api from '../../../services/admin/academics.ts'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AcademicSetup from './AcademicSetup.tsx'
import type { AcademicCatalogue, Department } from '../../../types/academicSetup.ts'

describe('Academic Setup permissions and session lifecycle', () => {
  it('uses server readable/manageable catalogues and hides write controls for read-only users', async () => {
    auth.user.effective_permissions = ['departments.read']
    catalogue.records = { departments: [department] }
    catalogue.manageable = []
    render(<AcademicSetup />)
    await screen.findByRole('heading', { name: department.name })
    expect(screen.getByText('Read-only access.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add|Edit|Deactivate/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Programs' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Academic years' })).not.toBeInTheDocument()
  })

  it('handles program-only access without exposing unavailable department records', async () => {
    catalogue.records = { programs: [] }
    catalogue.manageable = ['programs']
    render(<AcademicSetup />)
    expect(await screen.findByRole('heading', { name: 'Programs' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add degree program' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Departments' })).not.toBeInTheDocument()
  })

  it.each(['student', 'staff', 'faculty'])('does not fetch admin catalogue for role %s', (role) => {
    auth.role = role
    render(<AcademicSetup />)
    expect(screen.getByRole('status')).toHaveTextContent('Administrator access is unavailable.')
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
  })

  it('clears drafts and ignores a pending mutation after token and tenant replacement', async () => {
    let rejectOld: (cause: Error) => void = () => {
      throw new Error('Missing deferred rejection')
    }
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<Department>((_resolve, reject) => {
          rejectOld = reject
        }),
    )
    const view = render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add department' }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Old tenant draft' } })
    fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'OLD' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalled())
    auth.accessToken = 'token-2'
    auth.user.institution_id = 'institution-2'
    catalogue.records.departments = []
    view.rerender(<AcademicSetup />)
    await screen.findByText('No records yet.')
    await act(async () => {
      rejectOld(new Error('Old session failure'))
    })
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.queryByText('Old session failure')).not.toBeInTheDocument()
    expect(screen.queryByText('Saved successfully.')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenLastCalledWith('token-2')
    fireEvent.click(screen.getByRole('button', { name: 'Add department' }))
    expect(screen.getByLabelText('Name')).toHaveValue('')
  })

  it('ignores pending reads from a replaced session', async () => {
    let resolveOld: (value: AcademicCatalogue) => void = () => {
      throw new Error('Missing deferred resolution')
    }
    vi.mocked(api.getAcademicSetup).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve
        }),
    )
    const view = render(<AcademicSetup />)
    auth.accessToken = 'token-2'
    catalogue.records.departments = []
    view.rerender(<AcademicSetup />)
    await screen.findByText('No records yet.')
    await act(async () =>
      resolveOld({ institution_id: 'old-tenant', records: { departments: [department] }, manageable: ['departments'] }),
    )
    expect(screen.queryByRole('heading', { name: department.name })).not.toBeInTheDocument()
  })

  it('ignores a late successful save without closing the replacement session draft', async () => {
    let resolveOld: (value: Department) => void = () => {
      throw new Error('Missing deferred resolution')
    }
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<Department>((resolve) => {
          resolveOld = resolve
        }),
    )
    const view = render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add department' }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Old draft' } })
    fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'OLD' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalled())
    auth.accessToken = 'token-2'
    view.rerender(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add department' }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'New draft' } })
    await act(async () => resolveOld(department))
    expect(screen.getByLabelText('Name')).toHaveValue('New draft')
    expect(screen.queryByText('Saved successfully.')).not.toBeInTheDocument()
  })

  it('retains successful-save feedback and blocks duplicate retries until a failed refresh recovers', async () => {
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add department' }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Mechanical Engineering' } })
    fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'ME' } })
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Network unavailable'))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Saved successfully.')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not refresh Academic Setup')
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add department' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('heading', { name: 'Mechanical Engineering' })).toBeInTheDocument()
    expect(api.createAcademicRecord).toHaveBeenCalledOnce()
  })

  it('allows retrying the initial failed read', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Permission denied'))
    render(<AcademicSetup />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Permission denied')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('heading', { name: department.name })).toBeInTheDocument()
  })
})
