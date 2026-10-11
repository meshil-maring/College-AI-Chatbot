import { mergeConfig } from 'vitest/config'
import config from './vitest.config.ts'

// Local source tests only: never load dotenv files or call a real endpoint.
export default mergeConfig(config, {
  envDir: false,
  test: { setupFiles: ['./src/test/b05Offline.ts'] },
})
