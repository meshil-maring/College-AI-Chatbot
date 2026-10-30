import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import SemesterRegistrationCard from '../SemesterRegistrationCard.tsx'
import { semesterFixture } from './registrationFixture.ts'

describe('complete semester option selection', () => {
  it('requires one whole option and includes the two common subjects', () => {
    const onComplete = vi.fn().mockResolvedValue(undefined)
    render(<SemesterRegistrationCard semester={semesterFixture()} busy={false} canManage onComplete={onComplete} />)
    const submit = screen.getByRole('button', { name: 'Register selected subjects' })
    expect(submit).toBeDisabled()
    fireEvent.click(screen.getByRole('radio', { name: /Option 2/ }))
    expect(screen.getByText(/5 subjects selected/)).toBeInTheDocument()
    expect(submit).toBeEnabled()
    fireEvent.click(submit)
    expect(onComplete).toHaveBeenCalledExactlyOnceWith('registration-1', ['option-2'])
  })
  it('disables the entire option if one laboratory has no offering', () => {
    const semester = semesterFixture()
    semester.subjects[7].available = false
    render(<SemesterRegistrationCard semester={semester} busy={false} canManage onComplete={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /Option 2/ })).toBeDisabled()
    expect(screen.getByRole('radio', { name: /Option 1/ })).toBeEnabled()
  })
  it('blocks registration when a common required subject is unavailable', () => {
    const semester = semesterFixture()
    semester.subjects[0].available = false
    render(<SemesterRegistrationCard semester={semester} busy={false} canManage onComplete={vi.fn()} />)
    fireEvent.click(screen.getByRole('radio', { name: /Option 1/ }))
    expect(screen.getByRole('button', { name: 'Register selected subjects' })).toBeDisabled()
  })
  it('shows recorded subject snapshots after registration', () => {
    const semester = semesterFixture()
    semester.status = 'registered'
    semester.enrolled_subjects = [{ course_id: 'course-1', name: 'Original DSA name', code: 'CS1', credits: 4 }]
    render(<SemesterRegistrationCard semester={semester} busy={false} canManage onComplete={vi.fn()} />)
    expect(screen.getByText(/Original DSA name/)).toBeInTheDocument()
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })
})
