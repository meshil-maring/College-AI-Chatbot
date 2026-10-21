import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = fileURLToPath(new URL('../', import.meta.url))
const limit = 250
const folderLimit = 15
const limitedTrees = [
  path.join(frontend, 'src', 'services'),
  path.join(frontend, 'src', 'features', 'auth'),
  path.join(frontend, 'src', 'features', 'faculty'),
  path.join(frontend, 'src', 'features', 'student'),
]
const extensions = new Set(['.ts', '.tsx', '.css', '.js', '.mjs'])
const crowdedFolders = []

async function sourceFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  if (limitedTrees.some((root) => directory === root || directory.startsWith(root + path.sep))) {
    const directFiles = entries.filter((entry) => entry.isFile()).length
    if (directFiles > folderLimit) {
      crowdedFolders.push(`${path.relative(frontend, directory)}: ${directFiles} direct files`)
    }
  }
  const groups = await Promise.all(
    entries.map(async (entry) => {
      const filename = path.join(directory, entry.name)
      if (entry.isDirectory()) return sourceFiles(filename)
      return entry.isFile() && extensions.has(path.extname(filename)) ? [filename] : []
    }),
  )
  return groups.flat()
}

const rootFiles = (await readdir(frontend, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && extensions.has(path.extname(entry.name)))
  .map((entry) => path.join(frontend, entry.name))
const files = [
  ...rootFiles,
  ...(await sourceFiles(path.join(frontend, 'src'))),
  ...(await sourceFiles(path.join(frontend, 'scripts'))),
]
const oversized = []
for (const filename of files.sort()) {
  const content = await readFile(filename, 'utf8')
  const lines = content.split(/\r?\n/).length - (content.endsWith('\n') ? 1 : 0)
  if (lines > limit) oversized.push(`${path.relative(frontend, filename)}: ${lines} lines`)
}

if (oversized.length || crowdedFolders.length) {
  if (oversized.length) {
    console.error(`Split these files into focused modules (maximum ${limit} lines, including comments and blanks):`)
    console.error(oversized.join('\n'))
  }
  if (crowdedFolders.length) {
    console.error(`Group related files into subfolders (maximum ${folderLimit} direct files per folder):`)
    console.error(crowdedFolders.sort().join('\n'))
  }
  process.exitCode = 1
} else {
  console.log(
    `Structure check passed: ${files.length} code files are within ${limit} lines; service, auth, faculty, and student folders are within ${folderLimit} direct files.`,
  )
}
