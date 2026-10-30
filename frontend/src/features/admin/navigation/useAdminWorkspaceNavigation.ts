import { useLayoutEffect } from 'react'
import { navigateTo, useBrowserLocation } from '../../../lib/navigation.ts'
import { ADMIN_NAV_ITEMS, type AdminView } from '../adminNavigation.ts'
import { allAcademicAreas, type AcademicPage } from '../academic-setup/overview/academicOverviewModel.ts'

export function resolveAdminLocation(search: string) {
  const params = new URLSearchParams(search)
  const requestedView = params.get('view')
  const requestedPage = params.get('academic')
  const page: AcademicPage =
    requestedPage === 'overview' || requestedPage === 'records'
      ? requestedPage
      : (allAcademicAreas.find((area) => area.page === requestedPage)?.page ?? 'overview')
  const view: AdminView =
    ADMIN_NAV_ITEMS.find((item) => item.key === requestedView)?.key ??
    (requestedPage && page !== 'overview' ? 'academic-setup' : 'profile')
  return { view, page, search: params.get('academic-search') ?? '' }
}

export function useAdminWorkspaceNavigation(identity?: string) {
  const location = useBrowserLocation()
  const previousIdentity = window.history.state?.adminNavigationIdentity
  const replacedIdentity = Boolean(identity && previousIdentity && previousIdentity !== identity)
  const current = resolveAdminLocation(replacedIdentity ? '' : location.search)
  function open(view: AdminView, page: AcademicPage = current.page, search = '', replace = false) {
    const params = new URLSearchParams(window.location.search)
    if (view === 'profile') params.delete('view')
    else params.set('view', view)
    if (view === 'academic-setup') params.set('academic', page)
    else params.delete('academic')
    if (search.trim()) params.set('academic-search', search)
    else params.delete('academic-search')
    const query = params.toString()
    navigateTo(`${window.location.pathname}${query ? `?${query}` : ''}`, { replace })
  }
  useLayoutEffect(() => {
    if (!identity) return
    if (replacedIdentity) open('profile', 'overview', '', true)
    window.history.replaceState(
      { ...window.history.state, adminNavigationIdentity: identity },
      '',
      window.location.href,
    )
  }, [identity, replacedIdentity, location.pathname, location.search])
  return {
    selected: current.view,
    academicPage: current.page,
    academicSearch: current.search,
    navigateView: (view: AdminView) => open(view),
    navigateAcademic: (page: AcademicPage) => open('academic-setup', page),
    searchAcademic: (value: string) => open('academic-setup', 'overview', value, current.page === 'overview'),
    clearAcademicSearch: () => open('academic-setup', current.page, '', true),
  }
}
