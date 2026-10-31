import { ArrowRight, Compass } from 'lucide-react'
import type { AcademicPage } from '../overview/academicOverviewModel.ts'
import { academicDistinction, academicGuidance, academicJourney } from './academicJourney.ts'
import './journey.css'

export default function AcademicJourney({
  page,
  onNavigate,
}: {
  page: AcademicPage
  onNavigate: (page: AcademicPage) => void
}) {
  const guidance = academicGuidance(page)
  const distinction = academicDistinction(page)
  const currentStep = academicJourney.findIndex((step) => (step.pages as readonly string[]).includes(page))
  return (
    <section className="academic-journey" aria-label="Academic setup guide">
      <div className="academic-journey-heading">
        <Compass aria-hidden="true" />
        <div>
          <p className="academic-journey-title">From setup to student registration</p>
          <p>Start with foundations, then follow curriculum → intake → classes → enrollment.</p>
        </div>
      </div>
      <details className="academic-journey-steps" open={page === 'overview'}>
        <summary>
          {currentStep < 0
            ? 'Explore the five setup steps'
            : `Step ${currentStep + 1} of 5 · ${academicJourney[currentStep].title} · View setup steps`}
        </summary>
        <nav aria-label="Academic setup steps">
          <ol>
            {academicJourney.map((step, index) => {
              const current = (step.pages as readonly string[]).includes(page)
              return (
                <li key={step.id}>
                  <button
                    type="button"
                    aria-current={current ? 'step' : undefined}
                    onClick={() => onNavigate(step.page)}
                    title={step.description}
                  >
                    <span className="academic-step-number">{index + 1}</span>
                    <span>{step.title}</span>
                  </button>
                  <p className="academic-step-description">{step.description}</p>
                </li>
              )
            })}
          </ol>
        </nav>
      </details>
      {distinction && (
        <aside className="academic-journey-context" aria-label="Key distinction">
          <strong>{distinction.title}</strong>
          <p>{distinction.description}</p>
        </aside>
      )}
      {guidance && (
        <div className="academic-journey-next">
          <p>{guidance.description}</p>
          <button type="button" className="academic-secondary-button" onClick={() => onNavigate(guidance.next)}>
            {guidance.action}
            <ArrowRight aria-hidden="true" />
          </button>
        </div>
      )}
      {page === 'curriculum-versions' && (
        <button type="button" className="academic-journey-link" onClick={() => onNavigate('cohorts')}>
          Curriculum already published? Continue to Batches <ArrowRight aria-hidden="true" />
        </button>
      )}
    </section>
  )
}
