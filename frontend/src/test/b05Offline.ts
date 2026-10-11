import { beforeEach } from 'vitest'

beforeEach(() => {
  globalThis.fetch = async () => { throw new Error('B05 offline tests prohibit network requests') }
})
