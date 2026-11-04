import { beforeEach, describe, expect, it, vi } from 'vitest'
import { completeStudentSetup, inspectStudentSetup } from './studentOnboarding.ts'

beforeEach(() => {
  vi.unstubAllGlobals()
})

describe('student setup requests', () => {
  it('shows the backend setup error instead of mislabeling a 403 as closed registration', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'STUDENT_SETUP_REVIEW_REQUIRED',
              message: 'Student setup requires administrator review. Contact your institution administrator.',
            },
          }),
          {
            status: 403,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    )

    await expect(inspectStudentSetup('setup-token')).rejects.toThrow(
      'Student setup requires administrator review. Contact your institution administrator.',
    )
  })

  it('posts the setup token and password to the invitation completion endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: 'Setup complete.', completed: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(completeStudentSetup('setup-token', 'student-password')).resolves.toEqual({
      message: 'Setup complete.',
      completed: true,
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/student-onboarding/complete',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ token: 'setup-token', password: 'student-password' }),
      }),
    )
  })
})
