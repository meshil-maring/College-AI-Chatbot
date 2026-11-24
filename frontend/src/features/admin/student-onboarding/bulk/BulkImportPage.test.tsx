import { chooseSection, mocks, renderPage } from '../__tests__/onboarding.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

async function uploadCsv(user: ReturnType<typeof userEvent.setup>, contents: string) {
  await chooseSection(user)
  await user.click(screen.getByRole('button', { name: /Continue to upload/ }))
  const file = new File([contents], 'students.csv', { type: 'text/csv' })
  fireEvent.change(screen.getByLabelText('Choose student CSV or Excel file'), { target: { files: [file] } })
  await user.click(await screen.findByRole('button', { name: /Review student list/ }))
}

describe('Bulk Import page', () => {
  it('opens as a focused four-stage page with a way back to single registration', () => {
    renderPage({ bulkOnly: true })
    expect(screen.getByRole('heading', { level: 1, name: 'Bulk Student Import' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent('Students›Bulk Import›Placement')
    expect(screen.getByRole('list', { name: 'Registration steps' }).children).toHaveLength(4)
    expect(screen.getByRole('heading', { name: 'Where should these students be enrolled?' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Add one student/ })).not.toHaveAttribute(
      'href',
      expect.stringContaining('student-page='),
    )
  })

  it('guides bulk registration through upload, review, and row results', async () => {
    const user = userEvent.setup()
    renderPage({ bulkOnly: true })
    await uploadCsv(user, 'Student Name,Register Number,Email\nAda Lovelace,REG-1,ada@example.com')
    expect(screen.getByText('1 ready')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Invite 1 ready student/ }))
    expect(await screen.findByRole('heading', { name: 'Student invitations processed' })).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: 'Bulk registration results' })).getByText('Invitations created'),
    ).toBeInTheDocument()
    await waitFor(() => expect(mocks.createBulk).toHaveBeenCalledTimes(1))
  })

  it('filters duplicate and valid rows in the bulk import review', async () => {
    const user = userEvent.setup()
    renderPage({ bulkOnly: true })
    await uploadCsv(
      user,
      'Student Name,Register Number,Email\nAda Lovelace,REG-1,ada@example.com\nGrace Hopper,REG-1,grace@example.com',
    )

    expect(screen.getByRole('button', { name: /Valid 1/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Duplicate 1/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Duplicate 1/ }))
    expect(screen.getByRole('textbox', { name: 'Student Name row 3' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Student Name row 2' })).not.toBeInTheDocument()
  })
})
