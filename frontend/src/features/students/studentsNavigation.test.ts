import { describe, expect, it } from 'vitest'
import { resolveStudentsLocation, studentsPageHref } from './studentsNavigation.ts'

describe('student sidebar locations', () => {
  it('restores registration method and supports earlier bookmarked pages', () => {
    expect(studentsPageHref('admin', 'register', 'bulk')).toBe('#admin/students/register?method=bulk')
    expect(resolveStudentsLocation('admin', '#admin/students/register?method=bulk')).toEqual({ page: 'register', method: 'bulk' })
    expect(resolveStudentsLocation('admin', '#admin/students/import')).toEqual({ page: 'register', method: 'bulk' })
    expect(resolveStudentsLocation('admin', '#admin/students/requests')?.page).toBe('waiting-approval')
    expect(resolveStudentsLocation('admin', '#admin/students/all')?.page).toBe('roster')
  })
  it('accepts only known pages for the selected panel and keeps staff limited to approvals', () => {
    for (const hash of ['#staff/students/roster', '#staff/students/register', '#staff/students/record-history', '#admin/students/waiting-approval']) expect(resolveStudentsLocation('staff', hash)).toBeNull()
    expect(resolveStudentsLocation('staff', '#staff/students/waiting-approval')?.page).toBe('waiting-approval')
    for (const path of ['__proto__', 'constructor', 'unknown', 'roster/extra']) expect(resolveStudentsLocation('admin', `#admin/students/${path}`)).toBeNull()
  })
})
