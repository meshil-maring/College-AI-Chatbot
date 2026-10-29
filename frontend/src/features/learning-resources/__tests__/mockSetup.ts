import { beforeEach, vi } from 'vitest'
import type { CurrentUser } from '../../../types/auth.ts'
import { draft, indexedFiles, published, user } from './fixtures.ts'
import * as api from '../../../services/knowledge/resources.ts'

const auth = vi.hoisted(() => ({
  user: null as CurrentUser | null,
  accessToken: 'opaque-token',
  sessionGeneration: 12,
}))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({ ...auth, role: auth.user?.role ?? null, logout: () => undefined }),
}))
vi.mock('../../../services/knowledge/resources.ts', async (original) => ({
  ...(await original<typeof import('../../../services/knowledge/resources.ts')>()),
  listResources: vi.fn(),
  getResource: vi.fn(),
  getResourceChatContext: vi.fn(),
  getRevision: vi.fn(),
  createResource: vi.fn(),
  createRevision: vi.fn(),
  saveRevision: vi.fn(),
  uploadResourceFile: vi.fn(),
  retryResourceIndex: vi.fn(),
  decideRevision: vi.fn(),
}))
export const server = { revision: draft(), library: [published()] }
beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
  auth.user = user()
  auth.accessToken = 'opaque-token'
  auth.sessionGeneration = 12
  server.revision = draft()
  server.library = [published()]
  vi.mocked(api.getResourceChatContext).mockReset().mockResolvedValue({
    knowledge_source_id: server.library[0].knowledge_source_id,
    title: server.library[0].title,
    available: true,
  })
  vi.mocked(api.listResources)
    .mockReset()
    .mockImplementation(async (_token, view) => {
      const items = view === 'library' ? server.library : [server.revision]
      return structuredClone({ items, total: items.length })
    })
  vi.mocked(api.getResource)
    .mockReset()
    .mockImplementation(async () => structuredClone(server.library[0]))
  vi.mocked(api.getRevision)
    .mockReset()
    .mockImplementation(async () => structuredClone(server.revision))
  vi.mocked(api.createResource)
    .mockReset()
    .mockImplementation(async (_token, fields) => {
      server.revision = draft({
        ...fields,
        visibility:
          fields.audience.mode === 'public'
            ? 'public'
            : fields.audience.mode === 'institution'
              ? 'authenticated'
              : 'restricted',
        audience_roles: fields.audience.roles,
      })
      return structuredClone(server.revision)
    })
  vi.mocked(api.saveRevision)
    .mockReset()
    .mockImplementation(async (_token, _revision, fields, version) => {
      server.revision = {
        ...server.revision,
        ...fields,
        revision_version: version + 1,
        visibility:
          fields.audience.mode === 'public'
            ? 'public'
            : fields.audience.mode === 'institution'
              ? 'authenticated'
              : 'restricted',
        audience_roles: fields.audience.roles,
      }
      return structuredClone(server.revision)
    })
  vi.mocked(api.uploadResourceFile)
    .mockReset()
    .mockImplementation(async () => {
      server.revision = {
        ...server.revision,
        revision_version: server.revision.revision_version + 2,
        documents: indexedFiles(),
      }
      return structuredClone(server.revision)
    })
  vi.mocked(api.retryResourceIndex)
    .mockReset()
    .mockImplementation(async () => {
      server.revision = {
        ...server.revision,
        revision_version: server.revision.revision_version + 2,
        documents: indexedFiles(),
      }
      return structuredClone(server.revision)
    })
  vi.mocked(api.decideRevision)
    .mockReset()
    .mockImplementation(async (_token, _revision, action) => {
      const status = {
        submit: 'under_review',
        approve: 'approved',
        request_changes: 'draft',
        publish: 'published',
        unpublish: 'archived',
      } as const
      server.revision = {
        ...server.revision,
        lifecycle_status: status[action],
        revision_version: server.revision.revision_version + 1,
        policy_version: server.revision.policy_version + (['publish', 'unpublish'].includes(action) ? 1 : 0),
      }
      return structuredClone(server.revision)
    })
  vi.mocked(api.createRevision)
    .mockReset()
    .mockImplementation(async () => {
      server.revision = {
        ...server.revision,
        revision_id: 'next-revision',
        lifecycle_status: 'draft',
        revision_number: 2,
      }
      return structuredClone(server.revision)
    })
})
export { auth }
