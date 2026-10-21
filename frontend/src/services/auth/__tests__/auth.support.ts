import { beforeEach, vi } from 'vitest'
export const LOGIN_RESPONSE = {
  access_token: 'test-access-token',
  refresh_token: 'test-refresh-token',
  expires_in: 3600,
  message: 'Login successful.',
  user: { id: '71000000-0000-0000-0000-000000000001', email: 'meshil@example.com' },
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export async function lastCallBody(fetchMock: ReturnType<typeof vi.fn>): Promise<unknown> {
  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
  return JSON.parse(String(init.body))
}

beforeEach(() => {
  vi.unstubAllGlobals()
})
