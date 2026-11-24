// The in-app guide renders the same Markdown files kept in docs/user-guide, so
// the repository docs and the portal never drift apart.
import overview from '../../../../../../docs/user-guide/academic-setup/README.md?raw'
import foundations from '../../../../../../docs/user-guide/academic-setup/foundations.md?raw'
import curriculum from '../../../../../../docs/user-guide/academic-setup/curriculum.md?raw'
import batches from '../../../../../../docs/user-guide/academic-setup/batches-and-sections.md?raw'
import enrollment from '../../../../../../docs/user-guide/academic-setup/student-enrollment.md?raw'
import rules from '../../../../../../docs/user-guide/academic-setup/rules-and-troubleshooting.md?raw'

export interface GuideSection {
  id: string
  file: string
  title: string
  summary: string
  content: string
}

export const guideSections: readonly GuideSection[] = [
  { id: 'overview', file: 'README.md', title: 'Overview', summary: 'Key terms and the setup flow', content: overview },
  {
    id: 'foundations',
    file: 'foundations.md',
    title: 'Foundations',
    summary: 'Departments, programs, calendar, subjects',
    content: foundations,
  },
  {
    id: 'curriculum',
    file: 'curriculum.md',
    title: 'Curriculum',
    summary: 'Study plans, choices and publishing',
    content: curriculum,
  },
  {
    id: 'batches',
    file: 'batches-and-sections.md',
    title: 'Batches and sections',
    summary: 'Intake batches, class groups, section subjects',
    content: batches,
  },
  {
    id: 'enrollment',
    file: 'student-enrollment.md',
    title: 'Student enrollment',
    summary: 'Assigning students and subject registration',
    content: enrollment,
  },
  {
    id: 'rules',
    file: 'rules-and-troubleshooting.md',
    title: 'Rules and troubleshooting',
    summary: 'Enforced rules, messages and FAQs',
    content: rules,
  },
]

/** Maps a relative link inside the guide (e.g. `curriculum.md`) to its section id. */
export function guideSectionForLink(href: string | undefined) {
  if (!href || /^[a-z]+:/i.test(href) || href.startsWith('#')) return undefined
  const file = href.split('#')[0].split('/').pop()
  return guideSections.find((section) => section.file === file)?.id
}

/** Drops the repository-only navigation line ("← Previous · Next →") under each title. */
export function guideMarkdown(content: string) {
  return content.replace(/^\[←[^\n]*\n/m, '')
}
