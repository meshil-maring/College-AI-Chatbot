import { useEffect, useState } from 'react'

/** The timer unlocks the Retry control; it never sends a request. */
export function useRetryDelay(institution: string) {
  const [deadline, setDeadline] = useState(0)
  const [now, setNow] = useState(Date.now)
  useEffect(() => setDeadline(0), [institution])
  const remaining = Math.max(0, Math.ceil((deadline - now) / 1000))
  const waiting = remaining > 0
  useEffect(() => {
    if (!waiting) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [deadline, waiting])
  function wait(seconds: number | null) {
    const started = Date.now()
    setNow(started)
    setDeadline(started + Math.min(3600, Math.max(0, seconds ?? 0)) * 1000)
  }
  return { remaining, wait, clear: () => setDeadline(0), blocked: () => Date.now() < deadline }
}
