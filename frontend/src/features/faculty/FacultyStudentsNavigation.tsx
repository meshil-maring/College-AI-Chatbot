import { ClipboardList, History, Hourglass, UserPlus } from 'lucide-react'
import { navigateTo } from '../../lib/navigation.ts'
import { facultyStudentsPath, type FacultyStudentPage } from './facultyRoutes.ts'

const pages = [
  { page: 'roster', label: 'Roster', icon: ClipboardList },
  { page: 'history', label: 'Record history', icon: History },
  { page: 'waiting-approval', label: 'Waiting approval', icon: Hourglass },
  { page: 'register', label: 'Register', icon: UserPlus },
] as const

export default function FacultyStudentsNavigation({ page, sectionId, canRegister }: {
  page: FacultyStudentPage
  sectionId?: string
  canRegister: boolean
}) {
  return <nav aria-label="Students pages" className="flex flex-wrap gap-2 rounded-xl border border-[#26394e] bg-[#0d1c2c] p-2">
    {pages.map(({ page: target, label, icon: Icon }) => {
      const active = target === page
      const className = `inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[#ffc72c] ${active ? 'bg-[#3d3012] text-[#ffd03b]' : 'text-slate-300 hover:bg-[#142638] hover:text-white'}`
      if (target === 'register' && !canRegister) return <span key={target} aria-disabled="true" aria-current={active ? 'page' : undefined} className={`${className} cursor-not-allowed opacity-40`} title="Registration requires permission to manage this section"><Icon aria-hidden="true" size={17} />{label}</span>
      const href = facultyStudentsPath(sectionId, target)
      return <a key={target} href={href} aria-current={active ? 'page' : undefined} className={className} onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault()
        navigateTo(href)
      }}><Icon aria-hidden="true" size={17} />{label}</a>
    })}
  </nav>
}
