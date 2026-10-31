import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { resolveAdminLocation, useAdminWorkspaceNavigation } from '../useAdminWorkspaceNavigation.ts'

describe('administrator browser navigation', () => {
  it('restores known academic destinations and ignores unknown views', () => {
    expect(resolveAdminLocation('?view=academic-setup&academic=curriculum-options')).toMatchObject({
      view: 'academic-setup',
      page: 'curriculum-subjects',
    })
    expect(resolveAdminLocation('?view=academic-setup&academic=program-semesters')).toMatchObject({
      view: 'academic-setup',
      page: 'curriculum-subjects',
    })
    expect(resolveAdminLocation('?view=academic-setup&academic=enrollments')).toMatchObject({ page: 'enrollments' })
    expect(resolveAdminLocation('?view=unknown&academic=unknown')).toEqual({
      view: 'profile',
      page: 'overview',
      search: '',
    })
  })

  it('writes the combined curriculum destination for legacy semester links', () => {
    const hook = renderHook(useAdminWorkspaceNavigation)
    act(() => hook.result.current.navigateAcademic('program-semesters'))
    expect(hook.result.current.academicPage).toBe('curriculum-subjects')
    expect(window.location.search).toContain('academic=curriculum-subjects')
  })

  it('keeps direct navigation after remount and supports browser Back and Forward', async () => {
    window.history.replaceState(null, '', '/login/admin?institution=ALPHA')
    const hook = renderHook(useAdminWorkspaceNavigation)
    act(() => hook.result.current.navigateAcademic('curriculum-options'))
    expect(window.location.search).toContain('academic=curriculum-subjects')
    expect(window.location.search).toContain('institution=ALPHA')
    act(() => hook.result.current.navigateAcademic('enrollments'))
    expect(hook.result.current.academicPage).toBe('enrollments')
    act(() => window.history.back())
    await waitFor(() => expect(hook.result.current.academicPage).toBe('curriculum-subjects'))
    act(() => window.history.forward())
    await waitFor(() => expect(hook.result.current.academicPage).toBe('enrollments'))
    hook.unmount()
    const restored = renderHook(useAdminWorkspaceNavigation)
    expect(restored.result.current.selected).toBe('academic-setup')
    expect(restored.result.current.academicPage).toBe('enrollments')
  })

  it('stores search without adding a history entry for each keystroke', () => {
    const hook = renderHook(useAdminWorkspaceNavigation)
    act(() => hook.result.current.navigateAcademic('offerings'))
    const before = window.history.length
    act(() => hook.result.current.searchAcademic('C'))
    act(() => hook.result.current.searchAcademic('CSE'))
    expect(window.history.length).toBe(before + 1)
    expect(hook.result.current.academicSearch).toBe('CSE')
    act(() => hook.result.current.navigateAcademic('curriculum-options'))
    expect(hook.result.current.academicSearch).toBe('')
    expect(window.location.search).not.toContain('academic-search')
  })

  it('keeps other administrator views in the URL without academic filters', () => {
    const hook = renderHook(useAdminWorkspaceNavigation)
    act(() => hook.result.current.navigateView('approvals'))
    expect(window.location.search).toContain('view=approvals')
    expect(hook.result.current.selected).toBe('approvals')
    act(() => hook.result.current.navigateView('profile'))
    expect(window.location.search).not.toContain('view=')
    expect(hook.result.current.selected).toBe('profile')
  })

  it('retains a direct link on initial sign-in but resets another account’s saved view', () => {
    window.history.replaceState(null, '', '/?view=academic-setup&academic=curriculum-options')
    const first = renderHook(() => useAdminWorkspaceNavigation('account-a'))
    expect(first.result.current.academicPage).toBe('curriculum-subjects')
    act(() => first.result.current.navigateView('documents'))
    first.unmount()
    const replacement = renderHook(() => useAdminWorkspaceNavigation('account-b'))
    expect(replacement.result.current.selected).toBe('profile')
    expect(window.location.search).not.toContain('view=')
  })
})
