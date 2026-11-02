import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import DuplicateStudentConflictNotice from './DuplicateStudentConflictNotice.tsx'

describe('duplicate student conflict notice', () => {
  it('shows matching institution student details and sign-in state', () => {
    render(
      <DuplicateStudentConflictNotice
        message="Email, Register Number, or University Roll No. is already in use."
        review={{
          students: [
            {
              student_name: 'Ada Lovelace',
              email: 'ada@example.com',
              register_number: 'REG-1',
              university_roll_number: 'ROLL-1',
              approval_status: 'approved',
              account_status: 'active',
              student_status: 'active',
              is_active: true,
              has_signed_in: true,
              last_sign_in_at: null,
              matches_email: true,
              matches_register_number: false,
              matches_university_roll_number: false,
            },
          ],
          invitations: [],
          email_conflict_exists: true,
        }}
        reviewError=""
        reviewing={false}
      />,
    )

    expect(screen.getByText('Matching institution record')).toBeInTheDocument()
    expect(screen.getByText(/Ada Lovelace · ada@example.com · Register REG-1/)).toBeInTheDocument()
    expect(screen.getByText(/Signed in · Approval approved/)).toBeInTheDocument()
  })
})
