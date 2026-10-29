import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../services/chat/api.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import { turnKeys, turnStatusOptions } from './queries.ts'
import type { ChatRequest, ChatResponse } from '../../../types/chat.ts'

export interface RecoveryState {
  turnId: string
  request: ChatRequest | null
  retryable: boolean
  checking: boolean
  message: string
}

export function useTurnRecovery(
  identity: string,
  token: string | null,
  onRecovered: (response: ChatResponse, request: ChatRequest) => void,
  onDenied: (failure: unknown) => void,
) {
  const [state, setState] = useState<RecoveryState | null>(null)
  const active = useRef<{ turnId: string; request: ChatRequest | null } | null>(null)
  const version = useRef(0)
  const callbacks = useRef({ onRecovered, onDenied })
  callbacks.current = { onRecovered, onDenied }
  const owner = useRef(identity)
  owner.current = identity
  useEffect(
    () => () => {
      version.current += 1
      void queryClient.cancelQueries({ queryKey: turnKeys.scope(identity) })
      queryClient.removeQueries({ queryKey: turnKeys.scope(identity) })
    },
    [identity],
  )

  function clear() {
    version.current += 1
    if (active.current) {
      const queryKey = turnKeys.status(identity, active.current.turnId)
      void queryClient.cancelQueries({ queryKey })
      queryClient.removeQueries({ queryKey })
    }
    active.current = null
    setState(null)
  }
  function remember(request: ChatRequest | null, turnId = request?.turn_id) {
    if (!turnId) return
    version.current += 1
    active.current = { turnId, request }
    setState({
      turnId,
      request,
      retryable: false,
      checking: false,
      message: 'Your question may already be saved. Check for its reply before retrying.',
    })
  }
  async function check() {
    const selected = active.current
    if (!selected || !token) return
    const operation = version.current
    const current = () => operation === version.current && owner.current === identity && active.current === selected
    setState((previous) => (previous ? { ...previous, checking: true } : null))
    try {
      const status = await queryClient.fetchQuery(turnStatusOptions(identity, selected.turnId, token))
      if (!current()) return
      if (status.turn_id !== selected.turnId || status.request.turn_id !== selected.turnId)
        throw new ApiError(409, 'Reply scope changed')
      if (status.state === 'completed' && status.response) {
        callbacks.current.onRecovered(status.response, status.request)
        clear()
        return
      }
      active.current = { turnId: selected.turnId, request: status.request }
      setState({
        turnId: selected.turnId,
        request: status.request,
        retryable: status.retryable,
        checking: false,
        message: status.retryable
          ? 'The reply can be retried safely using your saved question.'
          : 'Your reply is still being prepared. Check again in a moment.',
      })
    } catch (failure) {
      if (!current()) return
      if (failure instanceof ApiError && [403, 409].includes(failure.status)) {
        clear()
        callbacks.current.onDenied(failure)
        return
      }
      const retryable = failure instanceof ApiError && failure.status === 404 && selected.request !== null
      setState((previous) =>
        previous
          ? {
              ...previous,
              checking: false,
              retryable,
              message: retryable
                ? 'This request was not saved. You can retry the same question safely.'
                : 'The saved reply could not be checked. Please check again.',
            }
          : null,
      )
    }
  }
  function restore(turnId: string) {
    remember(null, turnId)
    void check()
  }
  return { state, remember, check, clear, restore }
}
