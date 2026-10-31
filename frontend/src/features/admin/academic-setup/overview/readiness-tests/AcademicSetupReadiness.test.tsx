import '../../__tests__/AcademicSetup.support.ts'
import { catalogue, program } from '../../__tests__/AcademicSetup.support.ts'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AcademicWorkspace from '../AcademicWorkspace.tsx'
import { populateStructure } from '../../__tests__/academicStructureFixtures.ts'

describe('Academic setup program readiness', () => {
  it('switches readiness recommendations to the selected program only', async () => {
    populateStructure()
    const secondDepartment = {
      ...catalogue.records.departments![0],
      department_id: 'department-2',
      name: 'Mechanical Engineering',
      code: 'ME',
    }
    const secondProgram = {
      ...program,
      program_id: 'program-2',
      department_id: secondDepartment.department_id,
      name: 'B.Tech ME',
      code: 'BTECH-ME',
    }
    const subject = catalogue.records.courses![0]
    catalogue.records.departments!.push(secondDepartment)
    catalogue.records.courses!.push(
      { ...subject, course_id: 'course-2', department_id: secondDepartment.department_id, code: 'ME101' },
      { ...subject, course_id: 'course-3', department_id: secondDepartment.department_id, code: 'ME102' },
    )
    catalogue.records.programs = [
      structuredClone(program),
      secondProgram,
      { ...program, program_id: 'foreign-program', institution_id: 'foreign' },
    ]
    render(<AcademicWorkspace page="overview" search="" onNavigate={() => {}} onClearSearch={() => {}} />)
    const progress = await screen.findByRole('region', { name: 'Academic setup progress' })
    expect(
      await within(progress).findByRole('heading', { name: 'Enroll students in this program’s sections' }),
    ).toBeInTheDocument()
    expect(within(progress).getByText(/1 active reusable subject/)).toBeInTheDocument()
    const selector = within(progress).getByLabelText('Check readiness for')
    expect(within(selector).getAllByRole('option')).toHaveLength(2)
    fireEvent.change(selector, { target: { value: secondProgram.program_id } })
    expect(within(progress).getByRole('heading', { name: 'Create this program’s curriculum' })).toBeInTheDocument()
    expect(within(progress).getByText(/2 active reusable subjects/)).toBeInTheDocument()
    expect(within(progress).getByText(/0 published curricula/)).toBeInTheDocument()
  })
})
