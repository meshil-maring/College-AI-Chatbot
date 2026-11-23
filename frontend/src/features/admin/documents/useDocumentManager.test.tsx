/**
 * Document upload feedback: a loading toast while the request runs, replaced
 * by success once the server accepts the file. A failed upload keeps the
 * inline error and never reports success.
 */
import { act, renderHook, screen, waitFor } from '@testing-library/react'
import type { ChangeEvent } from 'react'
import { describe, expect, it, vi } from 'vitest'
import * as adminApi from '../../../services/admin/adminApi.ts'
import { useDocumentManager } from './useDocumentManager.ts'

vi.mock('../../../services/admin/adminApi.ts')
vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'token', user: { institution_id: 'inst-1' } }),
}))

function fileEvent() {
  const file = new File(['handbook'], 'handbook.pdf', { type: 'application/pdf' })
  return { target: { files: [file], value: 'handbook.pdf' } } as unknown as ChangeEvent<HTMLInputElement>
}

async function renderManager() {
  vi.mocked(adminApi.listKnowledgeSources).mockResolvedValue([{ knowledge_source_id: 'ks-1' }] as never)
  vi.mocked(adminApi.listDocuments).mockResolvedValue([])
  const hook = renderHook(() => useDocumentManager())
  await waitFor(() => expect(hook.result.current.knowledgeSourceId).toBe('ks-1'))
  return hook
}

describe('useDocumentManager upload notifications', () => {
  it('shows uploading, then success with processing started, after the server accepts the file', async () => {
    let accept: () => void = () => {}
    vi.mocked(adminApi.uploadDocument).mockReturnValue(
      new Promise((resolve) => {
        accept = () => resolve({} as never)
      }),
    )
    const { result } = await renderManager()
    let upload: Promise<void> = Promise.resolve()
    act(() => {
      upload = result.current.handleUpload(fileEvent())
    })
    expect(await screen.findByText('Uploading document...')).toBeInTheDocument()
    expect(screen.queryByText('Document uploaded successfully')).not.toBeInTheDocument()
    await act(async () => {
      accept()
      await upload
    })
    expect(await screen.findByText('Document uploaded successfully')).toBeInTheDocument()
    expect(screen.getByText('Document processing started.')).toBeInTheDocument()
    expect(screen.queryByText('Uploading document...')).not.toBeInTheDocument()
  })

  it('keeps the inline error and shows no success when the upload fails', async () => {
    vi.mocked(adminApi.uploadDocument).mockRejectedValue(new Error('File type is not supported.'))
    const { result } = await renderManager()
    await act(async () => {
      await result.current.handleUpload(fileEvent())
    })
    expect(result.current.error).toBe('File type is not supported.')
    await waitFor(() => expect(screen.queryByText('Uploading document...')).not.toBeInTheDocument())
    expect(screen.queryByText('Document uploaded successfully')).not.toBeInTheDocument()
  })
})
