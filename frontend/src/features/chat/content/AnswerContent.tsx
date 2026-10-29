import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { prepareAnswerMarkdown } from './prepareAnswerMarkdown.ts'
import './answer.css'

const components: Components = {
  h1: ({ children }) => <h3>{children}</h3>,
  h2: ({ children }) => <h3>{children}</h3>,
  a: ({ href, children }) =>
    href ? (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ) : (
      <span>{children}</span>
    ),
  table: ({ children }) => (
    <div className="chat-answer-table" role="region" aria-label="Answer table" tabIndex={0}>
      <table>{children}</table>
    </div>
  ),
}

/** Shared presentation for assistant replies; raw HTML stays escaped and images are omitted. */
export default function AnswerContent({ content }: { content: string }) {
  return (
    <div className="chat-answer text-reading">
      <Markdown remarkPlugins={[remarkGfm]} components={components} disallowedElements={['img', 'input']}>
        {prepareAnswerMarkdown(content)}
      </Markdown>
    </div>
  )
}
