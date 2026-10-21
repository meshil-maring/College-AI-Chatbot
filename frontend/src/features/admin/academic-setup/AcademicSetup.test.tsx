import './__tests__/AcademicSetup.support.tsx'
import { fixture, loaded, tab } from './__tests__/AcademicSetup.support.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'
import AcademicSetup, { usable } from './AcademicSetup.tsx'
describe('AcademicSetup', () => {
  it('creates branch batches and rejects invalid admission year ranges', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Batches')
    expect(screen.getByRole('heading', { name: 'Batches', exact: true })).toBeInTheDocument()
    expect(screen.getByText(/No batches have been entered/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Branch / program *'), { target: { value: 'p' } })
    fireEvent.change(screen.getByLabelText('Admission year *'), { target: { value: '2026' } })
    fireEvent.change(screen.getByLabelText('Completion year *'), { target: { value: '2025' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(screen.getByRole('alert')).toHaveTextContent('completion year 1 to 10 years later')
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Completion year *'), { target: { value: '2030' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() =>
      expect(api.saveAcademicRecord).toHaveBeenCalledWith(
        'jwt',
        'batches',
        { program_id: 'p', start_year: 2026, end_year: 2030, is_active: true },
        undefined,
      ),
    )
  })

  it('archives an existing batch while preserving its branch and admission years', async () => {
    const data = fixture()
    data.records.batches = [{ batch_id: 'batch-1', program_id: 'p', start_year: 2026, end_year: 2030, is_active: true }]
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Batches')
    expect(screen.getByText('2026–2030 · Science degree')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit 2026–2030' }))
    expect(screen.getByLabelText('Branch / program *')).toBeDisabled()
    expect(screen.getByLabelText('Admission year *')).toBeDisabled()
    expect(screen.getByLabelText('Completion year *')).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Active'))
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() =>
      expect(api.saveAcademicRecord).toHaveBeenCalledWith('jwt', 'batches', { is_active: false }, 'batch-1'),
    )
  })

  it('shows honest empty states and never creates data while loading', async () => {
    const data = fixture()
    Object.keys(data.records).forEach((key) => {
      data.records[key as keyof typeof data.records] = []
    })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    expect(screen.getByText(/No departments have been entered/)).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('creates a department without client actor or tenant fields', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Engineering' } })
    fireEvent.change(screen.getByLabelText('Code *'), { target: { value: 'ENG' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() =>
      expect(api.saveAcademicRecord).toHaveBeenCalledWith(
        'jwt',
        'departments',
        { name: 'Engineering', code: 'ENG', description: null, is_active: true },
        undefined,
      ),
    )
    expect(await screen.findByText('Academic record saved.')).toBeInTheDocument()
  })

  it('deactivates safely through an update and retains existing rows', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Edit SCI' }))
    fireEvent.click(screen.getByLabelText('Active'))
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() =>
      expect(api.saveAcademicRecord).toHaveBeenCalledWith(
        'jwt',
        'departments',
        expect.objectContaining({ is_active: false }),
        'd',
      ),
    )
    expect(screen.getByText('SCI · Science')).toBeInTheDocument()
  })

  it('offers only active departments when creating a program', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Programs')
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    const options = within(screen.getByLabelText('Department *'))
      .getAllByRole('option')
      .map((option) => option.textContent)
    expect(options).toContain('SCI · Science')
    expect(options).not.toContain('OLD · Archived')
  })

  it('cascades year/semester and program/curriculum subject selections', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    expect(within(screen.getByLabelText('Program *')).queryByText('BAD · Unavailable')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Program *'), { target: { value: 'p' } })
    fireEvent.change(screen.getByLabelText('Academic year *'), { target: { value: 'y' } })
    expect(within(screen.getByLabelText('Semester *')).queryByText('OTHER · Foreign term')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Semester *'), { target: { value: 's' } })
    expect(within(screen.getByLabelText('Course / subject *')).getByText('MATH · Mathematics')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Course / subject *')).queryByText('PHY · Physics')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Course / subject *'), { target: { value: 'c' } })
    fireEvent.change(screen.getByLabelText('Academic year *'), { target: { value: '' } })
    expect(screen.getByLabelText('Semester *')).toHaveValue('')
    expect(screen.getByLabelText('Course / subject *')).toHaveValue('')
  })

  it('prevents a semester date range outside its academic year', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Semesters')
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    for (const [name, value] of [
      ['Academic year *', 'y'],
      ['Name *', 'Term'],
      ['Code *', 'T'],
      ['Semester number *', '2'],
      ['Start date *', '2025-07-01'],
      ['End date *', '2026-12-31'],
    ])
      fireEvent.change(screen.getByLabelText(name), { target: { value } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Semester dates must fit')
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('keeps relationships fixed during edits and excludes them from patch payloads', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    tab('Course Offerings')
    fireEvent.click(screen.getByRole('button', { name: 'Edit offering' }))
    expect(screen.getByLabelText('Program *')).toBeDisabled()
    expect(screen.getByLabelText('Academic year *')).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Capacity'), { target: { value: '60' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() =>
      expect(api.saveAcademicRecord).toHaveBeenCalledWith(
        'jwt',
        'course_offerings',
        { capacity: 60, is_active: true },
        'o',
      ),
    )
  })

  it('respects read-only permission projections', async () => {
    const data = fixture()
    data.manageable = []
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await screen.findByText('Read-only access')
    expect(screen.queryByRole('button', { name: 'Add record' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit SCI' })).not.toBeInTheDocument()
  })

  it('surfaces duplicate errors without claiming success', async () => {
    vi.mocked(api.saveAcademicRecord).mockRejectedValue(new Error('Identifier already exists'))
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Edit SCI' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Identifier already exists')
    expect(screen.queryByText('Academic record saved.')).not.toBeInTheDocument()
  })

  it('retries unavailable reads without inventing records', async () => {
    vi.mocked(api.getAcademicCatalogue).mockRejectedValueOnce(new Error('Database unavailable'))
    render(<AcademicSetup accessToken="jwt" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Database unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }))
    await loaded()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('discards unsaved state when the session changes', async () => {
    const view = render(<AcademicSetup accessToken="old" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add record' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Unsaved old data' } })
    view.rerender(<AcademicSetup accessToken="new" />)
    await loaded()
    expect(screen.queryByDisplayValue('Unsaved old data')).not.toBeInTheDocument()
    expect(api.getAcademicCatalogue).toHaveBeenCalledWith('new')
  })

  it('propagates inactive academic ancestors to section availability', () => {
    const data = fixture(),
      offering = data.records.course_offerings![0]
    expect(usable(data, 'course_offerings', offering)).toBe(true)
    data.records.departments![0].is_active = false
    expect(usable(data, 'course_offerings', offering)).toBe(false)
  })
})
