import '@testing-library/jest-dom'
import { cleanup, configure } from '@testing-library/react'
import { toast } from 'sonner'
import { afterEach } from 'vitest'
import { queryClient } from '../lib/queryClient.ts'

// Match the bounded UI test budget on hosts where rendering several accessible
// forms can delay a settled request beyond Testing Library's one-second default.
configure({ asyncUtilTimeout: 5_000 })

afterEach(() => {
  // Toasts live in a module-level store; clear them so a later test's
  // Toaster does not replay feedback from an earlier one.
  toast.dismiss()
  cleanup()
  queryClient.clear()
  window.history.replaceState(null, '', '/')
})
