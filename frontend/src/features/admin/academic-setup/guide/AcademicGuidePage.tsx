import { useRef, useState } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, ArrowRight, BookOpenText } from 'lucide-react'
import { guideMarkdown, guideSectionForLink, guideSections } from './guideContent.ts'
import './guide.css'
import './guide-markdown.css'

interface Props {
  onOverview: () => void
}

/** Read-only administrator guide for Academic Setup, rendered from docs/user-guide. */
export default function AcademicGuidePage({ onOverview }: Props) {
  const [sectionId, setSectionId] = useState(guideSections[0].id)
  const articleRef = useRef<HTMLElement>(null)
  const index = guideSections.findIndex((section) => section.id === sectionId)
  const section = guideSections[index]
  const previous = guideSections[index - 1]
  const next = guideSections[index + 1]

  function open(id: string) {
    setSectionId(id)
    articleRef.current?.scrollIntoView?.({ block: 'start' })
    articleRef.current?.focus({ preventScroll: true })
  }

  const components: Components = {
    a: ({ href, children }) => {
      const target = guideSectionForLink(href)
      if (target)
        return (
          <button type="button" className="academic-guide-link" onClick={() => open(target)}>
            {children}
          </button>
        )
      if (href && /^https?:/i.test(href))
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      return <span>{children}</span>
    },
    table: ({ children }) => (
      <div className="academic-guide-table" role="region" aria-label="Guide table" tabIndex={0}>
        <table>{children}</table>
      </div>
    ),
  }

  return (
    <div className="academic-guide">
      <header className="academic-page-header">
        <div>
          <h1>Academic Setup User Guide</h1>
          <p>Step-by-step instructions with a worked example, from departments to student enrollment.</p>
        </div>
        <button type="button" className="academic-secondary-button" onClick={onOverview}>
          <ArrowLeft aria-hidden="true" /> Back to overview
        </button>
      </header>
      <div className="academic-guide-layout">
        <nav className="academic-guide-nav" aria-label="Guide sections">
          <p>
            <BookOpenText aria-hidden="true" /> Contents
          </p>
          <ol>
            {guideSections.map((item, position) => (
              <li key={item.id}>
                <button
                  type="button"
                  aria-current={item.id === sectionId ? 'page' : undefined}
                  onClick={() => open(item.id)}
                >
                  <span className="academic-guide-step">{position === 0 ? 'i' : position}</span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.summary}</small>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <article ref={articleRef} className="academic-guide-article" tabIndex={-1} aria-label={section.title}>
          <div className="academic-guide-markdown">
            <Markdown remarkPlugins={[remarkGfm]} components={components} disallowedElements={['img']}>
              {guideMarkdown(section.content)}
            </Markdown>
          </div>
          <footer className="academic-guide-pager">
            {previous ? (
              <button type="button" onClick={() => open(previous.id)}>
                <ArrowLeft aria-hidden="true" />
                <span>
                  <small>Previous</small>
                  {previous.title}
                </span>
              </button>
            ) : (
              <span />
            )}
            {next && (
              <button type="button" className="is-next" onClick={() => open(next.id)}>
                <span>
                  <small>Next</small>
                  {next.title}
                </span>
                <ArrowRight aria-hidden="true" />
              </button>
            )}
          </footer>
        </article>
      </div>
    </div>
  )
}
