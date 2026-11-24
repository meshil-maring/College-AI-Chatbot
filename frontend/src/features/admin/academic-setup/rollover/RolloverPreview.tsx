import type { RolloverPlan } from './rolloverPlan.ts'

function Tag({ exists }: { exists: boolean }) {
  return <span className={`rollover-tag${exists ? ' is-existing' : ''}`}>{exists ? 'Exists' : 'New'}</span>
}

export default function RolloverPreview({ plan }: { plan: RolloverPlan }) {
  const subjects = plan.sections.reduce((count, section) => count + section.subjects.length, 0)
  const termName = (number: number) => {
    const term = plan.terms.find((item) => item.number === number)
    return term?.existing?.name ?? term?.create.name ?? `Term ${number}`
  }
  return (
    <section className="rollover-preview" aria-label="Roll-over preview">
      <h3>Calendar</h3>
      <ul className="rollover-list">
        <li>
          <span>
            <strong>{plan.year.existing?.name ?? plan.year.create.name}</strong>
            <small>
              {plan.year.create.start_date} to {plan.year.create.end_date}
            </small>
          </span>
          <Tag exists={Boolean(plan.year.existing)} />
        </li>
        {plan.terms.map((term) => (
          <li key={term.number}>
            <span>
              {term.existing?.name ?? term.create.name}
              <small>
                {term.create.start_date} to {term.create.end_date}
              </small>
            </span>
            <Tag exists={Boolean(term.existing)} />
          </li>
        ))}
        {!plan.terms.length && <li className="rollover-empty">This year has no active terms to copy.</li>}
      </ul>
      <h3>
        Sections{' '}
        <small>
          ({plan.sections.length} sections, {subjects} subjects made available)
        </small>
      </h3>
      {plan.sections.length ? (
        <ul className="rollover-list">
          {plan.sections.map((section) => (
            <li key={section.key}>
              <span>
                <strong>
                  {section.batchLabel} · {section.section.name}
                </strong>
                <small>
                  Semester {section.stageNumber} · {termName(section.termNumber)} · {section.subjects.length} subject
                  {section.subjects.length === 1 ? '' : 's'}
                  {!section.subjects.length && ' (the curriculum has none for this semester yet)'}
                </small>
              </span>
              <Tag exists={Boolean(section.existingSectionId)} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="rollover-empty">No continuing sections need to be created.</p>
      )}
      {plan.skipped.length > 0 && (
        <>
          <h3>Not continued</h3>
          <ul className="rollover-list is-skipped">
            {plan.skipped.map((item) => (
              <li key={item.label}>
                <span>
                  {item.label}
                  <small>{item.reason}</small>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
