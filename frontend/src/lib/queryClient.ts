import { QueryClient } from '@tanstack/react-query'

/**
 * One client for the browser application. API modules remain responsible for
 * HTTP and contract/error handling; TanStack Query owns server-state lifetime,
 * deduplication, loading/error state, and invalidation.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 0,
      // Server state is scoped to the mounted experience. Removing inactive
      // entries prevents one authenticated test/session surface from leaking
      // data into a later mount or a replaced session.
      gcTime: 0,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})
