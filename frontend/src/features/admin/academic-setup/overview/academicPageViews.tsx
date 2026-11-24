import type { ReactNode } from 'react'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import type { AcademicPage } from './academicOverviewModel.ts'
import DepartmentsPage from '../departments/DepartmentsPage.tsx'
import ProgramsPage from '../programs/ProgramsPage.tsx'
import SubjectsPage from '../subjects/SubjectsPage.tsx'
import CurriculumPage from '../curriculum/CurriculumPage.tsx'
import BatchesPage from '../batches/BatchesPage.tsx'
import SectionsPage from '../sections/SectionsPage.tsx'
import StructureRecordsPage from '../structure/StructureRecordsPage.tsx'
import AcademicCalendarPage from '../calendar/AcademicCalendarPage.tsx'
import StudentEnrollmentPage from '../registration/StudentEnrollmentPage.tsx'
import AcademicGuidePage from '../guide/AcademicGuidePage.tsx'
import QuickSetupPage from '../quick-setup/QuickSetupPage.tsx'
import { calendarDestinations, calendarTabFor } from '../navigation/academicCalendarNavigation.ts'

export interface PageViewProps {
  page: AcademicPage
  context: StructureContext
  navigate: (page: AcademicPage) => void
  /** A "create" shortcut from the overview, consumed by the page that owns the entity. */
  createRequest: { entity?: AcademicEntity; create: boolean }
  clearRequest: () => void
}
type PageView = (props: PageViewProps) => ReactNode

const CURRICULUM_PAGES: readonly AcademicPage[] = [
  'curriculum',
  'curriculum-versions',
  'curriculum-subjects',
  'curriculum-options',
  'curriculum-history',
  'program-semesters',
]

function CurriculumView({ page, context, navigate }: PageViewProps) {
  const subjects = page === 'program-semesters' || page === 'curriculum-subjects' || page === 'curriculum-options'
  return (
    <CurriculumPage
      {...context}
      activeTab={subjects ? 'subjects' : page === 'curriculum-history' ? 'history' : 'versions'}
      onTabChange={(tab) =>
        navigate(
          tab === 'subjects' || tab === 'options'
            ? 'curriculum-subjects'
            : tab === 'history'
              ? 'curriculum-history'
              : 'curriculum-versions',
        )
      }
      onOverview={() => navigate('overview')}
      onBatches={() => navigate('cohorts')}
    />
  )
}

function CalendarView({ page, context, navigate, createRequest, clearRequest }: PageViewProps) {
  return (
    <AcademicCalendarPage
      {...context}
      initialTab="years"
      activeTab={calendarTabFor(page)}
      onTabChange={(tab) => navigate(calendarDestinations[tab])}
      createInitially={createRequest.entity === 'academic_years' && createRequest.create}
      onCreateHandled={clearRequest}
      onOverview={() => navigate('overview')}
    />
  )
}

/** Catalogue pages that can open straight into their "add" drawer from an overview shortcut. */
function catalogueView(Page: typeof DepartmentsPage, entity: AcademicEntity): PageView {
  return function CatalogueView({ context, navigate, createRequest, clearRequest }) {
    return (
      <Page
        {...context}
        createInitially={createRequest.entity === entity && createRequest.create}
        onCreateHandled={clearRequest}
        onOverview={() => navigate('overview')}
      />
    )
  }
}

const VIEWS: Partial<Record<AcademicPage, PageView>> = {
  departments: catalogueView(DepartmentsPage, 'departments'),
  programs: catalogueView(ProgramsPage, 'programs'),
  subjects: catalogueView(SubjectsPage, 'courses'),
  cohorts: ({ context, navigate }) => (
    <BatchesPage {...context} onOverview={() => navigate('overview')} onCreateSections={() => navigate('sections')} />
  ),
  sections: ({ context, navigate }) => (
    <SectionsPage {...context} onOverview={() => navigate('overview')} onEnrollment={() => navigate('enrollments')} />
  ),
  offerings: ({ page, context, navigate }) => (
    <StructureRecordsPage
      key={page}
      context={context}
      entity="academic_offerings"
      onOverview={() => navigate('overview')}
      filterBySection
    />
  ),
  enrollments: ({ context, navigate }) => (
    <StudentEnrollmentPage context={context} onBack={() => navigate('sections')} />
  ),
  guide: ({ navigate }) => <AcademicGuidePage onOverview={() => navigate('overview')} />,
  'quick-setup': ({ context, navigate }) => <QuickSetupPage context={context} onNavigate={navigate} />,
  ...Object.fromEntries(CURRICULUM_PAGES.map((page) => [page, CurriculumView])),
  ...Object.fromEntries(['calendar', ...Object.values(calendarDestinations)].map((page) => [page, CalendarView])),
}

/** The screen for an Academic Setup page; the overview is shown when there is none. */
export function academicPageView(page: AcademicPage): PageView | undefined {
  return VIEWS[page]
}
