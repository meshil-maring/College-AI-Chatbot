import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AnswerContent from './AnswerContent.tsx'
import { prepareAnswerMarkdown } from './prepareAnswerMarkdown.ts'
import MessageBubble from '../MessageBubble.tsx'
import { Message } from '../../publicChat/PublicChatMessages.tsx'

const answer = `This is a **draft sample**, not an officially approved college policy.

### Hostel rules

1. **Room allocation**
   - Obtain approval before changing rooms.
   - Keep your records up to date.
2. **Guests**
   - Overnight guests need permission.

Contact the hostel office for verified rules.`

describe('shared answer presentation', () => {
  it('renders paragraphs, emphasis, headings and nested lists', () => {
    const { container } = render(<AnswerContent content={answer} />)
    expect(screen.getByRole('heading', { name: 'Hostel rules' })).toBeInTheDocument()
    expect(container.querySelector('strong')).toHaveTextContent('draft sample')
    const ordered = container.querySelector('ol')!
    expect(ordered.children).toHaveLength(2)
    expect(within(ordered.children[0] as HTMLElement).getAllByRole('listitem')).toHaveLength(2)
    expect(container.querySelectorAll('ul')).toHaveLength(2)
    expect(container.textContent).not.toContain('**')
    expect(container.querySelectorAll('.chat-answer > p')).toHaveLength(2)
  })

  it.each(['public', 'authenticated'])('uses the same formatting in %s chat', (kind) => {
    render(
      <ol>
        {kind === 'public' ? (
          <Message message={{ id: 'answer', role: 'assistant', content: answer, status: 'success', createdAt: 1 }} />
        ) : (
          <MessageBubble message={{ id: 'answer', role: 'assistant', content: answer, status: 'success' }} />
        )}
      </ol>,
    )
    expect(screen.getByRole('heading', { name: 'Hostel rules' })).toBeInTheDocument()
    expect(screen.getByText('Overnight guests need permission.').closest('li')).toBeInTheDocument()
  })

  it.each(['public', 'authenticated'])('keeps %s user messages as literal text', (kind) => {
    render(
      <ol>
        {kind === 'public' ? (
          <Message message={{ id: 'question', role: 'user', content: '**My question**', createdAt: 1 }} />
        ) : (
          <MessageBubble message={{ id: 'question', role: 'user', content: '**My question**' }} />
        )}
      </ol>,
    )
    expect(screen.getByText('**My question**')).toBeInTheDocument()
    expect(document.querySelector('strong')).toBeNull()
  })

  it('escapes HTML, blocks executable links and omits remote images', () => {
    const { container } = render(
      <AnswerContent
        content={
          '<script>alert(1)</script>\n\n[Unsafe](javascript:alert%281%29)\n\n![tracking](https://example.test/pixel.png)'
        }
      />,
    )
    expect(container.querySelector('script, iframe, img')).toBeNull()
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Unsafe' })).not.toBeInTheDocument()
    expect(container.innerHTML).not.toContain('href="javascript:')
  })

  it('opens safe document links with the expected relationship', () => {
    render(<AnswerContent content="[Hostel office](https://college.example/hostel)" />)
    const link = screen.getByRole('link', { name: 'Hostel office' })
    expect(link).toHaveAttribute('href', 'https://college.example/hostel')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('preserves code indentation and renders tables in a keyboard-accessible scroll region', () => {
    const { container } = render(
      <AnswerContent
        content={
          '```text\n  first\n    second\n```\n\n| Rule | Detail |\n| --- | --- |\n| Guests | Approval required |'
        }
      />,
    )
    expect(container.querySelector('pre code')?.textContent).toBe('  first\n    second\n')
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Answer table' })).toHaveAttribute('tabindex', '0')
  })
})

describe('older collapsed responses', () => {
  it('restores numbered bold sections and clear inline bullets from existing saved answers', () => {
    const collapsed =
      'Draft sample only. 1. **Rooms**:- Ask for approval. - Keep records updated. 2. **Guests**: - Obtain permission.'
    const { container } = render(<AnswerContent content={collapsed} />)
    expect(container.querySelector('ol')?.children).toHaveLength(2)
    expect(container.querySelectorAll('ul > li')).toHaveLength(3)
    expect(screen.getByText('Draft sample only.')).toBeInTheDocument()
    expect(screen.getByText('Keep records updated.')).toBeInTheDocument()
  })

  it.each([
    answer,
    'The sample entry time is 9:00 PM and the fee is 1.25 units.',
    'Use `1. **Rooms** 2. **Guests**` as an example string.',
    'References: 2. **Second** and 4. **Fourth**.',
  ])('preserves existing layout, ordinary numbers and code: %s', (content) => {
    expect(prepareAnswerMarkdown(content)).toBe(content)
  })
})
