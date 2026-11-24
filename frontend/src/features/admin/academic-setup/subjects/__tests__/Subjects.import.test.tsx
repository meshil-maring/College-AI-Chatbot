import { api, renderSubjects } from './Subjects.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

async function openImport() {
  renderSubjects()
  const button = await screen.findByRole('button', { name: 'Import CSV' })
  await waitFor(() => expect(button).toBeEnabled(), { timeout: 5000 })
  fireEvent.click(button)
  return screen.findByRole('dialog', { name: 'Import Subjects' })
}

function upload(dialog: HTMLElement, text: string) {
  const file = new File([text], 'subjects.csv', { type: 'text/csv' })
  fireEvent.change(within(dialog).getByLabelText('Subject CSV file'), { target: { files: [file] } })
}

describe('Subject CSV import', () => {
  it('previews rows with errors and imports only valid new subjects into the chosen department', async () => {
    const dialog = await openImport()
    const importButton = within(dialog).getByRole('button', { name: /^Import \d+ rows?$/ })
    expect(importButton).toBeDisabled()
    fireEvent.change(within(dialog).getByRole('combobox', { name: /Department/ }), {
      target: { value: 'department-1' },
    })
    upload(dialog, 'code,name,credits\nNEW1,New Subject,3\n,Missing code,2')
    expect(await within(dialog).findByRole('status')).toHaveTextContent('1 new · 0 already exist · 1 with errors')
    expect(within(dialog).getByText('Code is required.')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Import 1 row' }))
    await waitFor(() => expect(within(dialog).getByText('Imported')).toBeInTheDocument())
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    expect(api.createAcademicRecord).toHaveBeenCalledWith('token-1', 'courses', {
      department_id: 'department-1',
      name: 'New Subject',
      code: 'NEW1',
      description: null,
      credits: 3,
      lecture_hours: null,
      tutorial_hours: null,
      practical_hours: null,
      is_active: true,
    })
    expect(await screen.findByText('Subjects imported successfully')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Done' })).toBeEnabled()
  })

  it('explains a file that cannot be used', async () => {
    const dialog = await openImport()
    upload(dialog, 'title\nAlgebra')
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('needs "code" and "name" columns')
  })
})
