import { useState } from 'react'
import { nameCodeError, semesterCount, splitYearIntoTerms } from '../quickSetupModel.ts'
import { ModeChoice, SelectField, StepFrame, TextField } from '../StepFrame.tsx'
import type { QuickSetupState } from '../useQuickSetup.ts'

export function CalendarStep({ setup }: { setup: QuickSetupState }) {
  const { years, terms } = setup.data
  const [mode, setMode] = useState<'existing' | 'new'>(years.length ? 'existing' : 'new')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [count, setCount] = useState('2')
  const needsTerms = mode === 'new' || (Boolean(setup.ids.year) && !terms.length)
  const plannedTerms =
    mode === 'new'
      ? splitYearIntoTerms(start, end, Number(count))
      : splitYearIntoTerms(setup.data.year?.start_date ?? '', setup.data.year?.end_date ?? '', Number(count))
  const problem =
    mode === 'existing'
      ? !setup.ids.year
        ? 'Choose an academic year.'
        : needsTerms && !plannedTerms.length
          ? 'Choose how many terms.'
          : ''
      : nameCodeError(name, code) || (!plannedTerms.length ? 'Enter a start date before the end date.' : '')
  return (
    <StepFrame
      setup={setup}
      title="Academic calendar"
      description="The academic year and its dated teaching terms. Terms say when classes run."
      onBack={() => setup.goTo('program')}
      continueLabel="Continue"
      continueDisabled={Boolean(problem)}
      onContinue={() =>
        void setup.perform(async () => {
          let yearId = setup.ids.year
          if (mode === 'new') {
            const year = await setup.api.createAcademic('academic_years', {
              name: name.trim(),
              code: code.trim(),
              start_date: start,
              end_date: end,
              is_current: false,
              is_active: true,
            })
            yearId = year.academic_year_id
            setup.choose('year', yearId)
          }
          if (needsTerms)
            for (const term of plannedTerms)
              await setup.api.createAcademic('semesters', {
                ...term,
                academic_year_id: yearId,
                is_current: false,
                is_active: true,
              })
        }, 'curriculum')
      }
    >
      <ModeChoice name="year-mode" mode={mode} hasExisting={years.length > 0} noun="academic year" onChange={setMode} />
      {mode === 'existing' ? (
        <SelectField
          label="Academic year"
          value={setup.ids.year}
          options={years.map((item) => ({ value: item.academic_year_id, label: item.name }))}
          onChange={(value) => setup.choose('year', value)}
        />
      ) : (
        <div className="quick-grid">
          <TextField label="Year name" value={name} onChange={setName} placeholder="2026 - 2027" />
          <TextField label="Year code" value={code} onChange={setCode} placeholder="AY2026" />
          <TextField label="Start date" type="date" value={start} onChange={setStart} />
          <TextField label="End date" type="date" value={end} onChange={setEnd} />
        </div>
      )}
      {mode === 'existing' && setup.ids.year && terms.length > 0 && (
        <p className="quick-note">This year already has {terms.map((term) => term.name).join(', ')}.</p>
      )}
      {needsTerms && (
        <>
          <TextField
            label="Number of terms"
            type="number"
            min={1}
            max={4}
            value={count}
            onChange={setCount}
            help="The year is split into equal, back-to-back terms. You can adjust their dates later."
          />
          {plannedTerms.length > 0 && (
            <ul className="quick-list">
              {plannedTerms.map((term) => (
                <li key={term.code}>
                  {term.name} · {term.start_date} to {term.end_date}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </StepFrame>
  )
}

export function CurriculumStep({ setup }: { setup: QuickSetupState }) {
  const { curricula, program, year, stages } = setup.data
  const [mode, setMode] = useState<'existing' | 'new'>(curricula.length ? 'existing' : 'new')
  const [name, setName] = useState(`${program?.code ?? 'Program'} ${year?.start_date.slice(0, 4) ?? ''}`.trim())
  const [version, setVersion] = useState('1.0')
  const total = semesterCount(program?.duration_years ?? 1)
  const chosen = curricula.find((item) => item.curriculum_version_id === setup.ids.curriculum)
  const problem =
    mode === 'existing'
      ? chosen
        ? ''
        : 'Choose a curriculum.'
      : nameCodeError(name, version) && 'Enter a name and version.'
  return (
    <StepFrame
      setup={setup}
      title="Curriculum"
      description={`A study plan with ${total} program semesters (two per year of study). It starts as a draft.`}
      onBack={() => setup.goTo('calendar')}
      continueLabel="Continue"
      continueDisabled={Boolean(problem)}
      onContinue={() =>
        void setup.perform(
          async () => {
            let semesters = chosen?.total_semesters ?? total
            if (mode === 'new') {
              const created = await setup.api.createStructure('curriculum_versions', {
                program_id: setup.ids.program,
                academic_year_id: setup.ids.year,
                name: name.trim(),
                version: version.trim(),
                total_semesters: total,
                description: null,
                is_active: true,
              })
              semesters = created.total_semesters
              setup.choose('curriculum', created.curriculum_version_id)
            }
            const existing = new Set(stages.map((stage) => stage.semester_number))
            for (let number = 1; number <= semesters; number += 1)
              if (!existing.has(number))
                await setup.api.createStructure('program_semesters', {
                  program_id: setup.ids.program,
                  semester_number: number,
                  name: `Semester ${number}`,
                  code: `SEM-${number}`,
                  is_active: true,
                })
          },
          chosen?.status === 'published' ? 'batch' : 'subjects',
        )
      }
    >
      <ModeChoice
        name="curriculum-mode"
        mode={mode}
        hasExisting={curricula.length > 0}
        noun="curriculum"
        onChange={setMode}
      />
      {mode === 'existing' ? (
        <SelectField
          label="Curriculum"
          value={setup.ids.curriculum}
          options={curricula.map((item) => ({
            value: item.curriculum_version_id,
            label: `${item.name} · v${item.version} (${item.status})`,
          }))}
          onChange={(value) => setup.choose('curriculum', value)}
        />
      ) : (
        <div className="quick-grid">
          <TextField label="Curriculum name" value={name} onChange={setName} />
          <TextField label="Version" value={version} onChange={setVersion} />
        </div>
      )}
      {chosen?.status === 'published' && (
        <p className="quick-note">This curriculum is already published, so the next step is the batch.</p>
      )}
    </StepFrame>
  )
}
