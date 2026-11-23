import '@testing-library/jest-dom'
import { cleanup, configure, render } from '@testing-library/react'
import { createElement } from 'react'
import { toast } from 'sonner'
import { afterEach, beforeEach } from 'vitest'
import { queryClient } from '../lib/queryClient.ts'
import { NotificationProvider } from '../providers/NotificationProvider.tsx'

// Match the bounded UI test budget on hosts where rendering several accessible
// forms can delay a settled request beyond Testing Library's one-second default.
configure({ asyncUtilTimeout: 5_000 })

// Production mounts one Toaster beside <App /> in main.tsx; mirror that so
// tests observe toast feedback through `screen` exactly as users see it.
beforeEach(() => {
  render(createElement(NotificationProvider))
})

afterEach(() => {
  // Toasts live in a module-level store; clear them so a later test's
  // Toaster does not replay feedback from an earlier one.
  toast.dismiss()
  cleanup()
  queryClient.clear()
  window.history.replaceState(null, '', '/')
})
