import { Check, ChevronRight } from 'lucide-react'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import type { AcademicPage } from '../overview/academicOverviewModel.ts'
import { QUICK_SETUP_STEPS } from './quickSetupModel.ts'
import { useQuickSetup } from './useQuickSetup.ts'
import { DepartmentStep, ProgramStep } from './steps/FoundationSteps.tsx'
import { CalendarStep, CurriculumStep } from './steps/PlanSteps.tsx'
import { PublishStep, SubjectsStep } from './steps/SubjectSteps.tsx'
import { BatchStep } from './steps/BatchStep.tsx'
import './quick-setup.css'

interface Props {
  context: StructureContext
  onNavigate: (page: AcademicPage) => void
}

/** Guided setup of one program from department to first-year sections, reusing existing records at each step. */
export default function QuickSetupPage({ context, onNavigate }: Props) {
  const setup = useQuickSetup(context)
  const current = setup.step === 'done' ? QUICK_SETUP_STEPS.length : setup.stepIndex
  return (
    <section className="academic-workspace quick-setup" aria-label="Quick setup">
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={() => onNavigate('overview')}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Quick Setup</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Quick Setup</h1>
          <p>Set up a program step by step. Each step saves before moving on, so you can stop and come back.</p>
        </div>
      </header>
      <ol className="quick-steps" aria-label="Setup steps">
        {QUICK_SETUP_STEPS.map((item, index) => {
          const state = index < current ? 'is-done' : index === current ? 'is-current' : ''
          return (
            <li key={item.id} className={state}>
              <button
                type="button"
                disabled={index > current || setup.saving || setup.step === 'done'}
                aria-current={index === current ? 'step' : undefined}
                onClick={() => setup.goTo(item.id)}
              >
                <span className="quick-step-marker" aria-hidden="true">
                  {index < current ? <Check /> : index + 1}
                </span>
                {item.title}
              </button>
            </li>
          )
        })}
      </ol>
      {setup.loading ? (
        <p role="status">Loading academic records…</p>
      ) : !setup.canManage ? (
        <p className="quick-note" role="status">
          Quick Setup needs permission to manage departments, subjects, curricula and sections.
        </p>
      ) : setup.step === 'done' ? (
        <section className="quick-step quick-done" aria-labelledby="quick-done-title">
          <h2 id="quick-done-title" tabIndex={-1}>
            {setup.data.program?.name ?? 'The program'} is ready
          </h2>
          <p>
            The curriculum is published, the batch exists and its first-year sections have their subjects. Next, assign
            students to sections.
          </p>
          <div className="quick-done-actions">
            <button type="button" className="academic-primary-button" onClick={() => onNavigate('enrollments')}>
              Assign students
            </button>
            <button type="button" className="academic-secondary-button" onClick={() => onNavigate('sections')}>
              Review sections
            </button>
            <button type="button" className="academic-secondary-button" onClick={() => onNavigate('overview')}>
              Back to overview
            </button>
          </div>
        </section>
      ) : setup.step === 'department' ? (
        <DepartmentStep setup={setup} />
      ) : setup.step === 'program' ? (
        <ProgramStep setup={setup} />
      ) : setup.step === 'calendar' ? (
        <CalendarStep setup={setup} />
      ) : setup.step === 'curriculum' ? (
        <CurriculumStep setup={setup} />
      ) : setup.step === 'subjects' ? (
        <SubjectsStep setup={setup} />
      ) : setup.step === 'publish' ? (
        <PublishStep setup={setup} />
      ) : (
        <BatchStep setup={setup} />
      )}
    </section>
  )
}
