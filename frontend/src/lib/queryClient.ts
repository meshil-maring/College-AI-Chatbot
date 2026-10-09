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
      // Features opt into bounded navigation caching below. Other queries
      // retain their existing lifetime within the mounted experience.
      gcTime: 0,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})

/** Retain recent reads in memory while navigating within one authenticated session. */
export const NAVIGATION_QUERY_POLICY = {
  staleTime: 60_000,
  gcTime: 5 * 60_000,
  refetchOnMount: true,
  meta: { navigationCache: true },
} as const

export function clearNavigationQueryCache(): void {
  // Removing queries also cancels their pending results so a retired session
  // cannot refill the cache after a logout or a token replacement.
  queryClient.removeQueries({ predicate: (query) => query.meta?.navigationCache === true })
}
