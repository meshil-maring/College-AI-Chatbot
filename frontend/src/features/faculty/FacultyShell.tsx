import { useState } from 'react'
import {
  Bell,
  BookOpen,
  CalendarCheck,
  ChevronDown,
  ClipboardCheck,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import {
  FACULTY_COMING_SOON_VIEWS,
  FACULTY_VIEW_HEADINGS,
  buildFacultyNavigation,
  type FacultyView,
} from './facultyNavigation.ts'
import FacultyDashboard from './FacultyDashboard.tsx'
import FacultyProfile from './FacultyProfile.tsx'
import FacultyAssignments from './FacultyAssignments.tsx'
import FacultyComingSoon from './FacultyComingSoon.tsx'
import FacultyAttendance from './FacultyAttendance.tsx'

type IconName = 'dashboard' | 'course' | 'sections' | 'students' | 'attendance' | 'tests' | 'results' | 'resources' | 'assistant' | 'notices' | 'settings' | 'logout'

const PORTAL_ICONS: Record<IconName, LucideIcon> = {
  dashboard: LayoutDashboard,
  course: BookOpen,
  sections: GraduationCap,
  students: Users,
  attendance: CalendarCheck,
  tests: ClipboardCheck,
  results: ClipboardCheck,
  resources: FileText,
  assistant: MessageCircle,
  notices: Bell,
  settings: Settings,
  logout: LogOut,
}

function PortalIcon({ name, size = 18 }: { name: IconName; size?: number }) {
  const Icon = PORTAL_ICONS[name]
  return <Icon aria-hidden="true" size={size} strokeWidth={1.8} />
}

const NAV_ICONS: Record<FacultyView, IconName> = {
  dashboard: 'dashboard', assignments: 'sections', students: 'students', attendance: 'attendance', results: 'results', notices: 'notices', resources: 'resources', assistant: 'assistant', profile: 'settings',
}

export default function FacultyShell() {
  const { user, role, accessToken, logout } = useAuth()
  const [view, setView] = useState<FacultyView>('dashboard')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const navigation = buildFacultyNavigation(role, user?.effective_permissions)
  const displayName = user?.email?.trim() || 'Faculty'
  const initials = displayName.slice(0, 2).toUpperCase()

  function navigate(nextView: FacultyView) {
    setView(nextView)
    setMobileNavOpen(false)
  }

  return (
    <div className="min-h-screen overflow-x-clip bg-[#07111d] text-slate-100">
      {mobileNavOpen ? <button type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} className="fixed inset-0 z-30 bg-black/60 lg:hidden" /> : null}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[244px] flex-col border-r border-[#1b2b3d] bg-[#081421] transition-transform lg:translate-x-0 ${mobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-[72px] items-center gap-3 border-b border-[#1b2b3d] px-6">
          <div className="relative flex h-9 w-9 items-center justify-center text-[#ffc72c]" aria-hidden="true"><GraduationCap className="h-9 w-9" strokeWidth={1.7} /></div>
          <div><p className="text-[19px] font-bold tracking-tight text-white">College <span className="text-[#ffc72c]">AI</span></p><p className="text-[11px] text-slate-400">Faculty Portal</p></div>
        </div>
        <div className="px-3 pt-5"><button type="button" onClick={() => navigate('assignments')} className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-slate-300 hover:bg-[#102235] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#ffc72c]"><span className="text-slate-400"><PortalIcon name="course" /></span>My Courses</button><button type="button" onClick={() => navigate('students')} className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-slate-300 hover:bg-[#102235] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#ffc72c]"><span className="text-slate-400"><PortalIcon name="students" /></span>My Students</button></div>
        <nav aria-label="Faculty navigation" className="flex-1 overflow-y-auto px-3 py-5">
          <div className="space-y-1">
            {navigation.map((item) => {
              const active = item.key === view
              return <div key={item.key}>
                <button type="button" onClick={() => navigate(item.key)} aria-current={active ? 'page' : undefined} className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium transition ${active ? 'bg-[#3d3012] text-[#ffd03b]' : 'text-slate-300 hover:bg-[#102235] hover:text-white'} focus:outline-none focus:ring-2 focus:ring-[#ffc72c]`}><span className={active ? 'text-[#ffc72c]' : 'text-slate-400 group-hover:text-slate-200'}><PortalIcon name={NAV_ICONS[item.key]} /></span><span className="truncate">{item.label}</span></button>
                {item.key === 'attendance' && active ? <div className="ml-10 mt-1 space-y-1 border-l border-[#3d3012] pl-3">{['Overview', 'Mark Attendance', 'Upload Attendance', 'Import History'].map((label) => <button key={label} type="button" onClick={() => navigate('attendance')} className={`block w-full rounded-md px-2 py-1.5 text-left text-xs ${label === 'Overview' ? 'bg-[#1f1e18] text-[#ffd03b]' : 'text-slate-400 hover:text-white'}`}>{label}</button>)}</div> : null}
              </div>
            })}
          </div>
        </nav>
        <div className="px-3 pb-5"><div className="my-1 border-t border-[#1b2b3d]" /><button type="button" onClick={() => navigate('results')} className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-slate-300 hover:bg-[#102235] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#ffc72c]"><span className="text-slate-400"><PortalIcon name="tests" /></span>Tests &amp; Assessments</button><button type="button" onClick={() => navigate('profile')} aria-current={view === 'profile' ? 'page' : undefined} className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium ${view === 'profile' ? 'bg-[#3d3012] text-[#ffd03b]' : 'text-slate-300 hover:bg-[#102235] hover:text-white'} focus:outline-none focus:ring-2 focus:ring-[#ffc72c]`}><span className="text-slate-400"><PortalIcon name="settings" /></span>Profile &amp; Settings</button><button type="button" aria-label="Sign out" onClick={logout} className="group mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-slate-300 hover:bg-[#102235] hover:text-white focus:outline-none focus:ring-2 focus:ring-[#ffc72c]"><span className="text-slate-400"><PortalIcon name="logout" /></span><span aria-hidden="true">Logout</span></button></div>
        <div className="border-t border-[#1b2b3d] p-4 text-[11px] text-slate-500">Authenticated faculty workspace</div>
      </aside>

      <div className="min-w-0 lg:pl-[244px]">
        <header className="sticky top-0 z-20 h-[72px] border-b border-[#1b2b3d] bg-[#091522]/95 backdrop-blur">
          <div className="flex h-full items-center gap-4 px-4 sm:px-6 lg:px-7">
            <button type="button" onClick={() => setMobileNavOpen(true)} aria-label="Show navigation" className="rounded-lg p-2 text-slate-300 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] lg:hidden"><Menu aria-hidden="true" className="h-5 w-5" /></button>
            <div className="min-w-0 flex-1"><div className="flex items-center gap-2 overflow-hidden text-xs text-slate-400"><span className="shrink-0 text-slate-300">Faculty Portal</span><span>›</span><span className="truncate">{FACULTY_VIEW_HEADINGS[view]}</span></div></div>
            <button type="button" aria-label="Notifications" className="relative rounded-lg p-2 text-slate-300 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c]"><Bell aria-hidden="true" className="h-5 w-5" /><span className="absolute right-0 top-0 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">3</span></button>
            <div className="hidden h-8 w-px bg-[#1b2b3d] sm:block" />
            <button type="button" onClick={() => navigate('profile')} className="flex items-center gap-2 rounded-lg px-1.5 py-1 text-left hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c]"><span className="sr-only">Signed in as {displayName}</span><span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#ffc72c]/70 bg-[#24354a] text-xs font-bold text-white">{initials}</span><span className="hidden max-w-[150px] sm:block"><span className="block truncate text-xs font-semibold text-white">{displayName}</span><span className="block text-[10px] text-slate-400">Faculty</span></span><ChevronDown aria-hidden="true" className="hidden h-4 w-4 text-slate-400 sm:block" /></button>
          </div>
        </header>
        <main className="mx-auto w-full min-w-0 max-w-[1380px] px-4 py-5 sm:px-6 lg:px-7 lg:py-6">
          {user === null ? <section role="status" className="rounded-2xl border border-[#26394e] bg-[#0d1c2c] p-8 text-center"><h1 className="text-2xl font-bold text-white">Faculty workspace unavailable</h1><p className="mt-3 text-sm text-slate-300">Your faculty identity could not be loaded. Please sign in again.</p><button type="button" onClick={logout} className="mt-6 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-[#ffc72c]">Sign out</button></section> : !navigation.some((item) => item.key === view) ? <section role="status" className="rounded-2xl border border-[#26394e] bg-[#0d1c2c] p-8 text-center"><h1 className="text-2xl font-bold text-white">No available views</h1><p className="mt-3 text-sm text-slate-300">Your account has no permissions for the selected faculty view.</p></section> : <>
            {view === 'dashboard' ? <><h1 className="mb-4 break-words text-2xl font-bold text-white">Dashboard</h1><FacultyDashboard user={user} onNavigate={navigate} /></> : null}
            {view === 'profile' ? <><h1 className="mb-4 break-words text-2xl font-bold text-white">Profile</h1><FacultyProfile user={user} /></> : null}
            {view === 'assignments' && accessToken !== null ? <><h1 className="mb-4 break-words text-2xl font-bold text-white">My Sections</h1><FacultyAssignments accessToken={accessToken} /></> : null}
            {view === 'attendance' && accessToken !== null ? <FacultyAttendance accessToken={accessToken} /> : null}
            {FACULTY_COMING_SOON_VIEWS.includes(view) && view !== 'attendance' ? <><h1 className="mb-4 break-words text-2xl font-bold text-white">{FACULTY_VIEW_HEADINGS[view]}</h1><FacultyComingSoon view={view} /></> : null}
            {view === 'assistant' ? <section aria-label="AI Assistant"><ChatShell /></section> : null}
          </>}
        </main>
      </div>
    </div>
  )
}
