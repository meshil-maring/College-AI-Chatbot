import '@testing-library/jest-dom'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'
import { queryClient } from '../lib/queryClient.ts'

// Match the bounded UI test budget on hosts where rendering several accessible
// forms can delay a settled request beyond Testing Library's one-second default.
configure({ asyncUtilTimeout: 5_000 })

afterEach(() => {
  cleanup()
  queryClient.clear()
  window.history.replaceState(null, '', '/')
})
