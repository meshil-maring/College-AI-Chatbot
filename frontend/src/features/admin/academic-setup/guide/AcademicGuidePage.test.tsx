import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AcademicGuidePage from './AcademicGuidePage.tsx'
import { guideMarkdown, guideSectionForLink } from './guideContent.ts'

describe('Academic Setup user guide', () => {
  it('opens on the overview and lists every guide section', () => {
    render(<AcademicGuidePage onOverview={vi.fn()} />)
    const contents = screen.getByRole('navigation', { name: 'Guide sections' })
    expect(within(contents).getAllByRole('button')).toHaveLength(6)
    expect(within(contents).getByRole('button', { name: /Overview/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { level: 1, name: 'Academic Setup guide' })).toBeInTheDocument()
  })

  it('moves between sections from the contents, the pager and links inside the guide', () => {
    render(<AcademicGuidePage onOverview={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Next\s*Foundations/ }))
    expect(screen.getByRole('heading', { level: 1, name: /Foundations/ })).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Curriculum →' })[0])
    expect(screen.getByRole('heading', { level: 1, name: /Curriculum/ })).toBeInTheDocument()
    const contents = screen.getByRole('navigation', { name: 'Guide sections' })
    fireEvent.click(within(contents).getByRole('button', { name: /Rules and troubleshooting/ }))
    expect(screen.getByRole('heading', { level: 1, name: 'Rules and troubleshooting' })).toBeInTheDocument()
  })

  it('returns to the overview', () => {
    const onOverview = vi.fn()
    render(<AcademicGuidePage onOverview={onOverview} />)
    fireEvent.click(screen.getByRole('button', { name: 'Back to overview' }))
    expect(onOverview).toHaveBeenCalledOnce()
  })
})

describe('guide content helpers', () => {
  it('maps only relative guide files to sections', () => {
    expect(guideSectionForLink('curriculum.md')).toBe('curriculum')
    expect(guideSectionForLink('./batches-and-sections.md#top')).toBe('batches')
    expect(guideSectionForLink('https://example.com/curriculum.md')).toBeUndefined()
    expect(guideSectionForLink('#key-terms')).toBeUndefined()
  })

  it('drops the repository navigation line under the title', () => {
    expect(guideMarkdown('# Title\n\n[← Back](README.md) · Next\n\nBody')).toBe('# Title\n\n\nBody')
  })
})
