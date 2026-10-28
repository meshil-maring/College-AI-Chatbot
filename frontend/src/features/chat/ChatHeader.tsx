import { Bot, History, Plus } from 'lucide-react'

interface Props {
  email?: string
  busy: boolean
  historyOpen: boolean
  onToggleHistory: () => void
  onNewChat: () => void
  onSignOut: () => void
}

export default function ChatHeader(props: Props) {
  return (
    <header className="border-b border-line bg-shell px-4 py-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={props.onToggleHistory}
          aria-label={props.historyOpen ? 'Close conversation history' : 'Open conversation history'}
          aria-expanded={props.historyOpen}
          className="flex items-center gap-2 rounded-lg border border-control px-3 text-sm text-content lg:hidden"
        >
          <History aria-hidden="true" size={18} />
          History
        </button>
        <Bot aria-hidden="true" className="text-accent" size={24} />
        <div>
          <h1 className="text-section font-semibold text-content">College AI Chatbot</h1>
          {props.email && <p className="text-xs text-muted">Signed in as {props.email}</p>}
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <button type="button" onClick={props.onNewChat} disabled={props.busy} className="ui-primary">
            <Plus aria-hidden="true" size={16} />
            New chat
          </button>
          <button
            type="button"
            onClick={props.onSignOut}
            className="rounded-lg border border-control px-3 text-sm text-content hover:bg-hover"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  )
}
