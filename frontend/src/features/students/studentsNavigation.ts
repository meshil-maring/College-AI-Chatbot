import { useSyncExternalStore } from 'react'

export const STUDENT_PAGES = [
  { key: 'roster', label: 'Roster', path: 'roster' },
  { key: 'history', label: 'Record history', path: 'record-history' },
  { key: 'waiting-approval', label: 'Waiting approval', path: 'waiting-approval' },
  { key: 'register', label: 'Register', path: 'register' },
] as const

export type StudentPage = typeof STUDENT_PAGES[number]['key']
export type StudentRegistrationMethod = 'individual' | 'bulk'
type StudentPanel = 'admin' | 'staff'

export function studentsPageHref(panel: StudentPanel, page: StudentPage, method: StudentRegistrationMethod = 'individual', sectionId?: string) {
  const path = STUDENT_PAGES.find((item) => item.key === page)!.path
  const query = new URLSearchParams({ ...(page === 'register' && method === 'bulk' ? { method: 'bulk' } : {}), ...(sectionId ? { section_id: sectionId } : {}) })
  return `#${panel}/students/${path}${query.size ? `?${query}` : ''}`
}

export function resolveStudentsLocation(panel: StudentPanel, hash: string) {
  const [path, query = ''] = hash.split('?')
  const prefix = `#${panel}/students/`
  if (!path.startsWith(prefix)) return null
  const segment = path.slice(prefix.length)
  // Keep bookmarks made before the shared navigation was introduced.
  const aliases: Record<string, StudentPage> = { all: 'roster', add: 'register', import: 'register', requests: 'waiting-approval' }
  const page = STUDENT_PAGES.find((item) => item.path === segment)?.key ?? (Object.hasOwn(aliases, segment) ? aliases[segment] : undefined)
  if (!page || (panel === 'staff' && page !== 'waiting-approval')) return null
  const method: StudentRegistrationMethod = page === 'register' && (segment === 'import' || new URLSearchParams(query).get('method') === 'bulk') ? 'bulk' : 'individual'
  const sectionId = new URLSearchParams(query).get('section_id')
  return { page, method, ...(sectionId ? { sectionId } : {}) }
}

function subscribe(onChange: () => void) {
  window.addEventListener('hashchange', onChange)
  window.addEventListener('popstate', onChange)
  return () => { window.removeEventListener('hashchange', onChange); window.removeEventListener('popstate', onChange) }
}

export function useStudentsLocation(panel: StudentPanel) {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash)
  return resolveStudentsLocation(panel, hash)
}

export function navigateStudents(panel: StudentPanel, page: StudentPage, method: StudentRegistrationMethod = 'individual', sectionId?: string, replace = false) {
  const hash = studentsPageHref(panel, page, method, sectionId)
  if (window.location.hash === hash) return
  window.history[replace ? 'replaceState' : 'pushState'](null, '', `${window.location.pathname}${window.location.search}${hash}`)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function leaveStudents() {
  if (!/^#(?:admin|staff)\/students\//.test(window.location.hash)) return
  window.history.pushState(null, '', `${window.location.pathname}${window.location.search}`)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
