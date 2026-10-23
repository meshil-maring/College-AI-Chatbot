import type { FacultyView } from './facultyNavigation.ts'

export const FACULTY_PATHS: Readonly<Record<FacultyView, string>> = {
  profile: '/faculty/profile',
  notices: '/faculty/notices',
  resources: '/faculty/resources',
  assistant: '/faculty/assistant',
}
export function resolveFacultyRoute(pathname: string): { view: FacultyView } | null {
  const path = pathname.replace(/\/+$/, '')
  if (path === '/faculty') return { view: 'profile' }
  const view = (Object.keys(FACULTY_PATHS) as FacultyView[]).find((key) => FACULTY_PATHS[key] === path)
  return view ? { view } : null
}
