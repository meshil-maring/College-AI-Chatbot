import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import { queryClient } from '../lib/queryClient.ts'

afterEach(() => {
  cleanup()
  queryClient.clear()
})
