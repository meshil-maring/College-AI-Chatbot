import type { ReactNode } from 'react'

/** Page title shared by Add Student and Bulk Import, with breadcrumb and one optional action. */
export default function OnboardingPageHeading({
  trail,
  title,
  description,
  action,
}: {
  trail: string[]
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <header className="student-onboarding-page-heading">
      <div>
        <nav className="student-onboarding-breadcrumb" aria-label="Breadcrumb">
          {trail.map((item, index) => (
            <span key={item} className="student-onboarding-breadcrumb-item">
              {index > 0 && <span aria-hidden="true">›</span>}
              <span aria-current={index === trail.length - 1 ? 'page' : undefined}>{item}</span>
            </span>
          ))}
        </nav>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  )
}
