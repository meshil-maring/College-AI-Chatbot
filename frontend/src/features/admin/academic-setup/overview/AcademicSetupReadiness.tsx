import { useState } from 'react'
import { ArrowRight, CircleCheck, CircleDashed } from 'lucide-react'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'
import type { AcademicPage } from './academicOverviewModel.ts'
import { activeAcademicPrograms, programReadiness } from './academicSetupReadinessModel.ts'

export default function AcademicSetupReadiness({
  catalogue,
  structure,
  loading,
  onNavigate,
}: {
  catalogue?: AcademicCatalogue
  structure?: StructureCatalogue
  loading: boolean
  onNavigate: (page: AcademicPage) => void
}) {
  const [selectedProgramId, setSelectedProgramId] = useState('')
  if (loading)
    return (
      <section className="academic-setup-readiness" aria-label="Academic setup progress" aria-busy="true">
        <h2>Program readiness</h2>
        <p aria-live="polite">Checking your saved setup…</p>
      </section>
    )

  if (!catalogue)
    return (
      <section className="academic-setup-readiness" aria-label="Academic setup progress">
        <h2>Program readiness</h2>
        <p aria-live="polite">Progress is unavailable until academic records can be loaded.</p>
      </section>
    )

  const programs = activeAcademicPrograms(catalogue)
  if (!programs)
    return (
      <section className="academic-setup-readiness" aria-label="Academic setup progress">
        <h2>Program readiness</h2>
        <p aria-live="polite">Progress is unavailable until academic records can be loaded.</p>
      </section>
    )

  if (!programs.length) {
    const hasDepartment = Boolean(
      catalogue.records.departments?.some((item) => item.institution_id === catalogue.institution_id && item.is_active),
    )
    return (
      <section className="academic-setup-readiness" aria-label="Academic setup progress">
        <div className="academic-readiness-heading">
          <div>
            <p>Program readiness</p>
            <h2>Set up a program</h2>
            <span>Create a program before preparing its curriculum.</span>
          </div>
          <button
            type="button"
            className="academic-primary-button"
            onClick={() => onNavigate(hasDepartment ? 'programs' : 'departments')}
          >
            {hasDepartment ? 'Set up a program' : 'Set up a department'} <ArrowRight aria-hidden="true" />
          </button>
        </div>
      </section>
    )
  }

  const selectedProgram = programs.find((program) => program.program_id === selectedProgramId) ?? programs[0]
  const readiness = programReadiness(catalogue, structure, selectedProgram.program_id)
  if (!readiness)
    return (
      <section className="academic-setup-readiness" aria-label="Academic setup progress">
        <h2>Program readiness</h2>
        <p aria-live="polite">Progress is unavailable until this program’s academic records can be loaded.</p>
      </section>
    )

  return (
    <section className="academic-setup-readiness" aria-label="Academic setup progress">
      <div className="academic-readiness-heading">
        <div>
          <p>Program readiness · {selectedProgram.name}</p>
          <h2>{readiness.nextAction}</h2>
          <span>{readiness.nextExplanation}</span>
        </div>
        <button type="button" className="academic-primary-button" onClick={() => onNavigate(readiness.nextPage)}>
          Continue <ArrowRight aria-hidden="true" />
        </button>
      </div>
      {programs.length > 1 && (
        <label className="academic-readiness-program">
          Check readiness for
          <select value={selectedProgram.program_id} onChange={(event) => setSelectedProgramId(event.target.value)}>
            {programs.map((program) => (
              <option key={program.program_id} value={program.program_id}>
                {program.name} ({program.code})
              </option>
            ))}
          </select>
        </label>
      )}
      <ol className="academic-readiness-steps">
        {readiness.steps.map((step, index) => (
          <li key={step.title} className={`is-${step.status}`}>
            <div className="academic-readiness-step-heading">
              {step.status === 'ready' ? <CircleCheck aria-hidden="true" /> : <CircleDashed aria-hidden="true" />}
              <span>
                {index + 1}. {step.title}
              </span>
              <small>{step.status.replace('-', ' ').replace(/^./, (letter) => letter.toUpperCase())}</small>
            </div>
            <p>{step.detail}</p>
          </li>
        ))}
      </ol>
      <p className="academic-readiness-note">
        Class sections aren’t needed to prepare a curriculum. Add them when this program needs separate class enrollment
        or subject offerings.
      </p>
    </section>
  )
}
