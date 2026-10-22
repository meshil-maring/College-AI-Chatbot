import { afterEach, expect, it, vi } from 'vitest'
import { commandAcademicPackage, getAcademicPackages } from './academicPackagesApi.ts'

afterEach(() => vi.unstubAllGlobals())

it('sends one authenticated package command without caller-controlled authority', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ assignment_id: 'saved' }), { status: 200 }))
  vi.stubGlobal('fetch', fetcher)
  await commandAcademicPackage('opaque-token', 'assign_package', { placement_id: 'placement', package_id: 'package' })
  expect(fetcher).toHaveBeenCalledWith(
    expect.stringContaining('/v1/academic-packages/assign_package'),
    expect.objectContaining({
      method: 'POST',
      headers: { Authorization: 'Bearer opaque-token', 'Content-Type': 'application/json' },
      body: JSON.stringify({ placement_id: 'placement', package_id: 'package' }),
    }),
  )
})

it('preserves server rejection messages and cancellable catalogue reads', async () => {
  const controller = new AbortController()
  const fetcher = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ error: { code: 'PACKAGE_LOCKED', message: 'Package changes are closed.' } }), {
      status: 409,
    }),
  )
  vi.stubGlobal('fetch', fetcher)
  await expect(getAcademicPackages('token', controller.signal)).rejects.toThrow('Package changes are closed.')
  expect(fetcher).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ signal: controller.signal }))
})
