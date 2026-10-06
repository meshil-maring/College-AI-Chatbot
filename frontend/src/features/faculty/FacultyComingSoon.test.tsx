/**
 * FacultyComingSoon tests — the placeholder must stay INERT.
 *
 * These tests pin the three honesty rules of the "Coming Soon" contract:
 * no network request, no invented data, and no actionable controls.
 */

/// <reference types="vitest/globals" />
import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import FacultyComingSoon from './FacultyComingSoon.tsx'
import {
  FACULTY_COMING_SOON_VIEWS,
  FACULTY_VIEW_HEADINGS,
} from './facultyNavigation.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('FacultyComingSoon', () => {
  it('labels the section Coming Soon and states plainly that no information exists', () => {
    render(<FacultyComingSoon view="students" />)
    expect(screen.getByText('Coming Soon')).toBeInTheDocument()
    expect(
      screen.getByText('No information is available for this section yet.'),
    ).toBeInTheDocument()
    // Honest wording, not a delivery promise.
    expect(
      screen.getByText(/Nothing on this page is loaded or simulated\./),
    ).toBeInTheDocument()
  })

  it('performs zero requests for every Coming Soon view', () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    for (const view of FACULTY_COMING_SOON_VIEWS) {
      render(<FacultyComingSoon view={view} />)
    }
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('offers no actionable controls for any Coming Soon view', () => {
    for (const view of FACULTY_COMING_SOON_VIEWS) {
      const { unmount } = render(<FacultyComingSoon view={view} />)
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
      expect(screen.queryByRole('link')).not.toBeInTheDocument()
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      unmount()
    }
  })

  it('never renders numeric data of any kind (no fake counts or statistics)', () => {
    for (const view of FACULTY_COMING_SOON_VIEWS) {
      const { unmount } = render(<FacultyComingSoon view={view} />)
      const text = screen.getByRole('region', { name: 'Coming soon' }).textContent ?? ''
      expect(text).not.toMatch(/\d/)
      unmount()
    }
  })

  it('renders a heading-sized section body consistent with every Coming Soon view', () => {
    for (const view of FACULTY_COMING_SOON_VIEWS) {
      expect(FACULTY_VIEW_HEADINGS[view]).toBeTruthy()
      const { unmount } = render(<FacultyComingSoon view={view} />)
      expect(screen.getByRole('region', { name: 'Coming soon' })).toBeInTheDocument()
      unmount()
    }
  })
})