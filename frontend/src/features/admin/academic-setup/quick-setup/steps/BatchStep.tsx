import { useState } from 'react'
import { batchYears, nameCodeError, sectionLetters } from '../quickSetupModel.ts'
import { ModeChoice, SelectField, StepFrame, TextField } from '../StepFrame.tsx'
import type { QuickSetupState } from '../useQuickSetup.ts'

export function BatchStep({ setup }: { setup: QuickSetupState }) {
  const { program, year, terms, stages, mappings, records } = setup.data
  const batches = setup.data.batches.filter((item) => item.curriculum_version_id === setup.ids.curriculum)
  const years = batchYears(year?.start_date ?? '0000', program?.duration_years ?? 1)
  const [mode, setMode] = useState<'existing' | 'new'>(batches.length ? 'existing' : 'new')
  const [name, setName] = useState(`${program?.code ?? 'Batch'} ${years.start_year}`)
  const [code, setCode] = useState(`${program?.code ?? 'B'}${String(years.start_year).slice(2)}`)
  const [count, setCount] = useState('1')
  const [capacity, setCapacity] = useState('60')
  const letters = sectionLetters(Number(count) || 1)
  const firstYear = terms
    .map((term) => ({ term, stage: stages.find((stage) => stage.semester_number === term.semester_number) }))
    .filter((item) => item.stage)
  const problem = mode === 'existing' ? (setup.ids.batch ? '' : 'Choose a batch.') : nameCodeError(name, code)
  return (
    <StepFrame
      setup={setup}
      title="Batch and first-year sections"
      description="The intake batch for this curriculum, and its class sections for each term of the first year."
      onBack={() => setup.goTo('publish')}
      continueLabel="Create and finish"
      continueDisabled={Boolean(problem) || !(Number(capacity) > 0)}
      onContinue={() =>
        void setup.perform(async () => {
          let batchId = setup.ids.batch
          if (mode === 'new') {
            const batch = await setup.api.createStructure('admission_cohorts', {
              program_id: setup.ids.program,
              curriculum_version_id: setup.ids.curriculum,
              academic_year_id: setup.ids.year,
              name: name.trim(),
              code: code.trim(),
              ...years,
              expected_count: null,
              description: null,
              status: 'active',
            })
            batchId = batch.admission_cohort_id
            setup.choose('batch', batchId)
          }
          for (const { term, stage } of firstYear) {
            const subjects = mappings.filter(
              (item) => item.is_active && item.program_semester_id === stage!.program_semester_id,
            )
            for (const letter of letters) {
              const exists = (records?.academic_sections ?? []).some(
                (item) =>
                  item.admission_cohort_id === batchId &&
                  item.program_semester_id === stage!.program_semester_id &&
                  item.code.toLowerCase() === letter.toLowerCase(),
              )
              if (exists) continue
              const section = await setup.api.createStructure('academic_sections', {
                admission_cohort_id: batchId,
                program_semester_id: stage!.program_semester_id,
                semester_id: term.semester_id,
                name: `Section ${letter}`,
                code: letter,
                capacity: Number(capacity),
                description: null,
                is_active: true,
              })
              for (const subject of subjects)
                await setup.api.createStructure('academic_offerings', {
                  academic_section_id: section.academic_section_id,
                  curriculum_subject_id: subject.curriculum_subject_id,
                  capacity: null,
                  is_active: true,
                })
            }
          }
        }, 'done')
      }
    >
      <ModeChoice name="batch-mode" mode={mode} hasExisting={batches.length > 0} noun="batch" onChange={setMode} />
      {mode === 'existing' ? (
        <SelectField
          label="Batch"
          value={setup.ids.batch}
          options={batches.map((item) => ({ value: item.admission_cohort_id, label: `${item.name} (${item.code})` }))}
          onChange={(value) => setup.choose('batch', value)}
        />
      ) : (
        <div className="quick-grid">
          <TextField label="Batch name" value={name} onChange={setName} />
          <TextField label="Batch code" value={code} onChange={setCode} />
          <p className="quick-note">
            Runs {years.start_year} to {years.end_year}, from the intake year and the program duration.
          </p>
        </div>
      )}
      <div className="quick-grid">
        <TextField label="Sections per semester" type="number" min={1} max={26} value={count} onChange={setCount} />
        <TextField label="Capacity per section" type="number" min={1} value={capacity} onChange={setCapacity} />
      </div>
      <ul className="quick-list" aria-label="Sections to create">
        {firstYear.map(({ term, stage }) => (
          <li key={term.semester_id}>
            {stage!.name} in {term.name}: Section {letters.join(', ')} with{' '}
            {mappings.filter((item) => item.program_semester_id === stage!.program_semester_id).length} subjects each
          </li>
        ))}
        {!firstYear.length && <li>This academic year has no terms, so no sections will be created.</li>}
      </ul>
    </StepFrame>
  )
}
