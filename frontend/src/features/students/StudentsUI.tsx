import { useId, type ReactNode } from 'react'
import { ChevronRight, Search, type LucideIcon } from 'lucide-react'
import './students.css'

export function StudentsPageHeader({ page, title, description, actions, onStudents }: {
  page: string
  title?: string
  description?: string
  actions?: ReactNode
  onStudents?: () => void
}) {
  return <>
    <nav aria-label="Breadcrumb" className="students-breadcrumb">
      {onStudents ? <button type="button" onClick={onStudents}>Students</button> : <span>Students</span>}
      <ChevronRight aria-hidden="true" />
      <span aria-current="page">{page}</span>
    </nav>
    {title && <StudentsPageTitle title={title} description={description} actions={actions} />}
  </>
}

export function StudentsPageTitle({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return <div className="students-title"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="students-heading-actions">{actions}</div>}</div>
}

export interface StudentsNavItem<Key extends string> {
  key: Key
  label: string
  href: string
  disabled?: boolean
  title?: string
}

export function StudentsNavigation<Key extends string>({ id, items, active, onNavigate }: {
  id: string
  items: readonly StudentsNavItem<Key>[]
  active: Key
  onNavigate: (key: Key) => void
}) {
  return <nav id={id} aria-label="Students pages" className="students-page-links">
    {items.map((item) => item.disabled
      ? <span key={item.key} aria-disabled="true" aria-current={item.key === active ? 'page' : undefined} title={item.title}>{item.label}</span>
      : <a key={item.key} href={item.href} aria-current={item.key === active ? 'page' : undefined} className={item.key === active ? 'active' : ''} onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault()
        onNavigate(item.key)
      }}>{item.label}</a>)}
  </nav>
}

export type RegistrationMethod = 'individual' | 'bulk'

export function StudentRegistrationMethods({ mode, onChange, disabled = false, placement, children }: {
  mode: RegistrationMethod
  onChange: (mode: RegistrationMethod) => void
  disabled?: boolean
  placement?: ReactNode
  children: ReactNode
}) {
  const id = useId()
  return <>
    <div role="tablist" aria-label="Registration method" className="students-tabs students-tabs-bar">
      {(['individual', 'bulk'] as const).map((tab) => <button key={tab} id={`${id}-${tab}`} role="tab" type="button" aria-selected={mode === tab} aria-controls={`${id}-panel`} tabIndex={mode === tab ? 0 : -1} className={mode === tab ? 'active' : ''} disabled={disabled} onClick={() => onChange(tab)} onKeyDown={(event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
        event.preventDefault()
        const next = event.key === 'Home' ? 'individual' : event.key === 'End' ? 'bulk' : mode === 'individual' ? 'bulk' : 'individual'
        onChange(next)
        document.getElementById(`${id}-${next}`)?.focus()
      }}>{tab === 'individual' ? 'Individual Registration' : 'Bulk Registration'}</button>)}
    </div>
    {placement}
    <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-${mode}`}>{children}</div>
  </>
}

export function StudentsStats({ items }: { items: {
  key: string
  title: string
  description: string
  value: string | number
  Icon: LucideIcon
  tone?: string
  selected: boolean
  onSelect: () => void
}[] }) {
  return <div className="students-stats">{items.map(({ key, title, description, value, Icon, tone = '', selected, onSelect }) => <button key={key} type="button" className={`students-stat ${tone} ${selected ? 'is-selected' : ''}`} aria-pressed={selected} onClick={onSelect}>
    <span className="students-stat-icon"><Icon aria-hidden="true" /></span>
    <span><strong>{typeof value === 'number' ? value.toLocaleString() : value}</strong><b>{title}</b><small>{description}</small></span>
  </button>)}</div>
}

export function StudentsSearch({ value, onChange, onSubmit, label = 'Search students', placeholder = 'Name, register number, roll number or email' }: {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  label?: string
  placeholder?: string
}) {
  return <form className="students-search-form" onSubmit={(event) => { event.preventDefault(); onSubmit() }}>
    <label className="students-search"><Search aria-hidden="true" /><input type="search" aria-label={label} maxLength={128} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>
    <button type="submit" className="students-button"><Search aria-hidden="true" />Search</button>
  </form>
}
