/**
 * Phase 6.16 — Student data loading primitives.
 *
 * `useStudentResource` is the single data-loading primitive behind every
 * authenticated student surface. It exists so that the four UI states are
 * never conflated:
 *
 *   idle    — no access token (the shell is not rendered in this state)
 *   loading — the request is in flight
 *   loaded  — the request succeeded (the payload may still be empty)
 *   error   — the request failed with a user-safe message + retry
 *
 * Performance: each hook instance issues ONE request and only re-issues it when
 * the access token changes or the caller explicitly retries. The dashboard
 * mounts six independent instances, so its six loads run CONCURRENTLY (React
 * runs each instance's effect independently) — there is no request→wait→request
 * chain. No polling and no caching layer is introduced.
 *
 * Session lifecycle (Phase 6.15.7, reused verbatim): a 401 from any student
 * endpoint raises the existing global session-expiry notification inside
 * `services/studentApi.ts`; AuthProvider clears the session and the login
 * screen takes over. This hook adds no second mechanism — when the token
 * disappears the section simply returns to `idle`.
 *
 * Failure isolation: one failing request only changes ITS OWN section state,
 * so a single unavailable endpoint cannot blank the rest of the dashboard.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'

export type SectionStatus = 'idle' | 'loading' | 'loaded' | 'error'

export interface SectionState<T> {
  readonly status: SectionStatus
  readonly data: T | null
  /** User-safe failure message; never backend internals. */
  readonly error: string | null
}

export interface StudentResourceState<T> extends SectionState<T> {
  readonly reload: () => void
}

const IDLE_STATE: SectionState<never> = { status: 'idle', data: null, error: null }

/**
 * Load one student resource for the authenticated session.
 *
 * @param loader       Stable async loader receiving the access token. Callers
 *                     pass a module-level function; the hook keeps the latest
 *                     reference in a ref, so an inline arrow cannot cause a
 *                     reload loop.
 * @param errorMessage User-safe message shown when the request fails.
 */
export function useStudentResource<T>(
  loader: (accessToken: string) => Promise<T>,
  errorMessage: string,
): StudentResourceState<T> {
  const { accessToken } = useAuth()
  const [state, setState] = useState<SectionState<T>>(IDLE_STATE as SectionState<T>)

  // Latest loader/message without re-triggering the effect.
  const loaderRef = useRef(loader)
  loaderRef.current = loader
  const errorMessageRef = useRef(errorMessage)
  errorMessageRef.current = errorMessage

  // Discards results from superseded requests (token change / retry), so a late
  // response can never overwrite the current section state.
  const generationRef = useRef(0)

  const load = useCallback((): void => {
    if (accessToken === null) {
      generationRef.current += 1
      setState(IDLE_STATE as SectionState<T>)
      return
    }
    generationRef.current += 1
    const generation = generationRef.current
    setState({ status: 'loading', data: null, error: null })
    void loaderRef.current(accessToken)
      .then((data) => {
        if (generationRef.current !== generation) return
        setState({ status: 'loaded', data, error: null })
      })
      .catch(() => {
        if (generationRef.current !== generation) return
        // The thrown message is intentionally not surfaced: the API client
        // already normalizes backend errors to user-safe text, and this fixed
        // message stays stable per section.
        setState({ status: 'error', data: null, error: errorMessageRef.current })
      })
  }, [accessToken])

  useEffect(() => {
    load()
  }, [load])

  return { ...state, reload: load }
}
