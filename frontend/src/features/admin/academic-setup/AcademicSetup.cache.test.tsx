import './__tests__/AcademicSetup.support.tsx'
import { fixture, loaded, tab } from './__tests__/AcademicSetup.support.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { QueryObserver } from '@tanstack/react-query'
import * as api from '../../../services/admin/adminApi.ts'
import * as packagesApi from '../../../services/academics/academicPackagesApi.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import AcademicSetup from './AcademicSetup.tsx'

const releaseQueries: (() => void)[] = []
afterEach(() => releaseQueries.splice(0).forEach((release) => release()))

function retainPackageQuery(token: string) {
  const observer = new QueryObserver(queryClient, {
    queryKey: ['academic-packages', token],
    enabled: false,
    staleTime: 30_000,
  })
  releaseQueries.push(observer.subscribe(() => {}))
}

it('refreshes curriculum branch options after a program is created in College basics', async () => {
  // Keep this query observed while navigating so gcTime=0 cannot hide missing invalidation.
  retainPackageQuery('jwt')
  retainPackageQuery('other-token')
  queryClient.setQueryData(['academic-packages', 'other-token'], { options: { programs: [] } })
  const data = fixture()
  data.records.programs = []
  vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
  vi.mocked(packagesApi.getAcademicPackages).mockImplementation(async () => ({
    institution_id: 'tenant',
    capabilities: ['manage_curriculum'],
    records: {},
    options: { programs: (data.records.programs ?? []).map((row) => ({ ...row })) },
  }))
  vi.mocked(api.saveAcademicRecord).mockImplementation(async (_token, entity, payload) => {
    expect(entity).toBe('programs')
    data.records.programs!.push({ ...payload, program_id: 'new-program' })
    return { program_id: 'new-program' }
  })
  render(<AcademicSetup accessToken="jwt" />)
  await loaded()
  const workflow = within(screen.getByRole('navigation', { name: 'Academic setup workflow' }))
  fireEvent.click(workflow.getByRole('button', { name: '4 Curricula & packages' }))
  expect(within(await screen.findByLabelText('Course / branch')).getAllByRole('option')).toHaveLength(1)
  await waitFor(() => expect(workflow.getByRole('button', { name: '1 College basics' })).toBeEnabled())
  tab('Programs')
  fireEvent.click(screen.getByRole('button', { name: 'Add Program' }))
  for (const [name, value] of [
    ['Department *', 'd'],
    ['Name *', 'Computer Science'],
    ['Code *', 'CSE'],
    ['Degree type *', 'B.Tech'],
    ['Duration in years *', '4'],
  ])
    fireEvent.change(screen.getByLabelText(name), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
  await screen.findByText('Academic record saved.')
  await waitFor(() => expect(workflow.getByRole('button', { name: '4 Curricula & packages' })).toBeEnabled())
  fireEvent.click(workflow.getByRole('button', { name: '4 Curricula & packages' }))
  await waitFor(() =>
    expect(
      within(screen.getByLabelText('Course / branch')).getByRole('option', {
        name: /Computer Science/,
      }),
    ).toHaveValue('new-program'),
  )
  expect(packagesApi.getAcademicPackages).toHaveBeenCalledTimes(2)
  expect(queryClient.getQueryState(['academic-packages', 'other-token'])?.isInvalidated).toBe(false)
})

it('keeps cached curriculum options valid when a foundational record save fails', async () => {
  retainPackageQuery('jwt')
  retainPackageQuery('other-token')
  queryClient.setQueryData(['academic-packages', 'jwt'], { options: { programs: [] } })
  queryClient.setQueryData(['academic-packages', 'other-token'], { options: { programs: [] } })
  vi.mocked(api.saveAcademicRecord).mockRejectedValue(new Error('Program code already exists'))
  render(<AcademicSetup accessToken="jwt" />)
  await loaded()
  tab('Programs')
  fireEvent.click(screen.getByRole('button', { name: 'Add Program' }))
  for (const [name, value] of [
    ['Department *', 'd'],
    ['Name *', 'Computer Science'],
    ['Code *', 'CSE'],
    ['Degree type *', 'B.Tech'],
    ['Duration in years *', '4'],
  ])
    fireEvent.change(screen.getByLabelText(name), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Program code already exists')
  expect(queryClient.getQueryState(['academic-packages', 'jwt'])?.isInvalidated).toBe(false)
  expect(queryClient.getQueryState(['academic-packages', 'other-token'])?.isInvalidated).toBe(false)
  expect(packagesApi.getAcademicPackages).not.toHaveBeenCalled()
})
