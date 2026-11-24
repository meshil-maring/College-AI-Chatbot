import '../../__tests__/AcademicSetup.support.ts'
import { catalogue, structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
import * as api from '../../../../../services/admin/academics.ts'
import * as structureApi from '../../../../../services/admin/academicStructure.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

const KEYS = {
  departments: 'department_id',
  programs: 'program_id',
  academic_years: 'academic_year_id',
  semesters: 'semester_id',
  courses: 'course_id',
} as const

beforeEach(() => {
  catalogue.manageable = ['departments', 'programs', 'academic_years', 'semesters', 'courses']
  Object.assign(catalogue.records, { academic_years: [], semesters: [], courses: [] })
  let serial = 0
  vi.mocked(api.createAcademicRecord).mockImplementation(async (_token, entity, payload) => {
    const record = { ...payload, [KEYS[entity]]: `${entity}-${++serial}`, institution_id: catalogue.institution_id }
    catalogue.records[entity]!.push(record as never)
    return record as never
  })
})

function Workspace() {
  const [page, setPage] = useState<AcademicPage>('quick-setup')
  return <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
}

const step = (name: string) => screen.findByRole('heading', { level: 2, name })
const change = (label: string | RegExp, value: string) =>
  fireEvent.change(screen.getByLabelText(label, { selector: 'input, select' }), { target: { value } })
const next = async (label = 'Continue') => {
  const button = screen.getByRole('button', { name: label })
  await waitFor(() => expect(button).toBeEnabled())
  fireEvent.click(button)
}

describe('Quick Setup', () => {
  it('sets up a program from department to first-year sections', async () => {
    render(<Workspace />)
    await step('Department')
    change('Department', 'department-1')
    await next()

    await step('Program')
    change('Program name', 'B.Tech Computer Science')
    change('Program code', 'BTCS')
    await next()
    expect(api.createAcademicRecord).toHaveBeenCalledWith(
      'token-1',
      'programs',
      expect.objectContaining({
        department_id: 'department-1',
        duration_years: 4,
      }),
    )

    await step('Academic calendar')
    change('Year name', '2026 - 2027')
    change('Year code', 'AY2026')
    change('Start date', '2026-08-01')
    change('End date', '2027-07-31')
    expect(screen.getByText('Term 2 · 2027-01-30 to 2027-07-31')).toBeInTheDocument()
    await next()

    await step('Curriculum')
    expect(screen.getByLabelText('Curriculum name')).toHaveValue('BTCS 2026')
    await next()

    await step('Subjects')
    expect(
      vi.mocked(structureApi.createStructureRecord).mock.calls.filter(([, e]) => e === 'program_semesters'),
    ).toHaveLength(8)
    const file = new File(['code,name,credits,semester\nCS101,Programming,4,1\nCS102,Data Structures,4,2'], 's.csv')
    fireEvent.change(screen.getByLabelText('Subject CSV file'), { target: { files: [file] } })
    fireEvent.click(await screen.findByRole('button', { name: 'Import 2 rows' }))
    await waitFor(() =>
      expect(within(screen.getByLabelText('Subjects per semester')).getAllByText('1 subject')).toHaveLength(2),
    )
    await next('Continue to publish')

    await step('Publish the curriculum')
    await next('Publish and continue')
    expect(structureApi.updateStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'curriculum_versions',
      expect.any(String),
      {
        status: 'published',
      },
    )

    await step('Batch and first-year sections')
    expect(screen.getByText(/Runs 2026 to 2030/)).toBeInTheDocument()
    await next('Create and finish')
    expect(await screen.findByRole('heading', { name: 'B.Tech Computer Science is ready' })).toBeInTheDocument()
    const created = vi.mocked(structureApi.createStructureRecord).mock.calls
    expect(created.filter(([, e]) => e === 'admission_cohorts')[0][2]).toMatchObject({
      start_year: 2026,
      end_year: 2030,
    })
    expect(created.filter(([, e]) => e === 'academic_sections').map(([, , p]) => (p as { code: string }).code)).toEqual(
      ['A', 'A'],
    )
    expect(created.filter(([, e]) => e === 'academic_offerings')).toHaveLength(2)
    expect(structureCatalogue.records.academic_sections).toHaveLength(2)
  }, 30_000)

  it('keeps the step and explains a failed save', async () => {
    vi.mocked(api.createAcademicRecord).mockRejectedValueOnce(new Error('A department with this code already exists.'))
    render(<Workspace />)
    await step('Department')
    fireEvent.click(screen.getByRole('radio', { name: 'Create a new department' }))
    change('Department name', 'Physics')
    change('Department code', 'CSE')
    await next()
    expect(await screen.findByRole('alert')).toHaveTextContent('A department with this code already exists.')
    expect(screen.getByRole('heading', { level: 2, name: 'Department' })).toBeInTheDocument()
  })
})
