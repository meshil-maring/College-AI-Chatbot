import '../integration/__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import StudentShell from './StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'

it('mounts only the reduced student navigation after account approval', async () => {
  mockAllLoaded()
  render(<StudentShell />)
  const navigation = await screen.findByRole('navigation', { name: 'Student navigation' })
  expect(
    within(navigation)
      .getAllByRole('button')
      .map((item) => item.textContent),
  ).toEqual(['Profile', 'Notices', 'Learning Resources', 'AI Assistant'])
  expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Academic context' })).not.toBeInTheDocument()
})
