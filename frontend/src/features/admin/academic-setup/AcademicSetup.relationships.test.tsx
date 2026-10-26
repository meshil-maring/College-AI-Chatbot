import './__tests__/AcademicSetup.support.ts'
import { catalogue } from './__tests__/AcademicSetup.support.ts'
import { populateExportCatalogue, semester, course, section, offering } from './__tests__/academicExportFixtures.ts'
import * as api from '../../../services/admin/academics.ts'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AcademicSetup from './AcademicSetup.tsx'

describe('academic relationship choices and immutable parents', () => {
  it('keeps the offering and section code immutable when editing capacity', async () => {
    populateExportCatalogue()
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Sections', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: `Edit ${section.name}` }))
    expect(screen.getByLabelText('Code', { exact: true })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Course offering' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Capacity (optional)'), { target: { value: '25' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(api.updateAcademicRecord).toHaveBeenCalledWith('token-1', 'sections', section.section_id, {
        name: section.name,
        capacity: 25,
        is_active: true,
      }),
    )
  })

  it('filters offerings by active ancestry and hides foreign tenant parents', async () => {
    populateExportCatalogue()
    catalogue.records.course_offerings = [{ ...offering, institution_id: 'foreign-tenant' }]
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Sections', exact: true }))
    expect(screen.getByRole('button', { name: 'Add section' })).toBeDisabled()
  })

  it('offers only linked courses and semesters in the selected year', async () => {
    populateExportCatalogue()
    catalogue.records.courses!.push({ ...course, course_id: 'unlinked-course', name: 'Unlinked' })
    catalogue.records.semesters!.push({
      ...semester,
      semester_id: 'foreign-semester',
      academic_year_id: 'another-year',
      name: 'Other term',
    })
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Course offerings', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Add course offering' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Academic year' }), {
      target: { value: offering.academic_year_id },
    })
    fireEvent.change(screen.getByRole('combobox', { name: 'Degree program' }), {
      target: { value: offering.program_id },
    })
    expect(screen.queryByRole('option', { name: /Unlinked/ })).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Course' }), { target: { value: course.course_id } })
    expect(screen.queryByRole('option', { name: /Other term/ })).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: `${semester.name} (${semester.code})` })).toBeInTheDocument()
  })

  it('shows read-only offerings with their course and program names', async () => {
    populateExportCatalogue()
    catalogue.manageable = []
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Course offerings', exact: true }))
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(course.name)
    expect(screen.queryByRole('button', { name: /Add course offering|Edit|Deactivate/ })).not.toBeInTheDocument()
  })
})
