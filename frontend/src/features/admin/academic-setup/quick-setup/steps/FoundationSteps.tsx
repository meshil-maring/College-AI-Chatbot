import { useState } from 'react'
import { nameCodeError } from '../quickSetupModel.ts'
import { ModeChoice, SelectField, StepFrame, TextField } from '../StepFrame.tsx'
import type { QuickSetupState } from '../useQuickSetup.ts'

export function DepartmentStep({ setup }: { setup: QuickSetupState }) {
  const { departments } = setup.data
  const [mode, setMode] = useState<'existing' | 'new'>(departments.length ? 'existing' : 'new')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const problem = mode === 'new' ? nameCodeError(name, code) : setup.ids.department ? '' : 'Choose a department.'
  return (
    <StepFrame
      setup={setup}
      title="Department"
      description="The department that will own the program and its subjects."
      continueLabel="Continue"
      continueDisabled={Boolean(problem)}
      onContinue={() =>
        void setup.perform(async () => {
          if (mode === 'existing') return
          const created = await setup.api.createAcademic('departments', {
            name: name.trim(),
            code: code.trim(),
            description: null,
            is_active: true,
          })
          setup.choose('department', created.department_id)
        }, 'program')
      }
    >
      <ModeChoice
        name="department-mode"
        mode={mode}
        hasExisting={departments.length > 0}
        noun="department"
        onChange={setMode}
      />
      {mode === 'existing' ? (
        <SelectField
          label="Department"
          value={setup.ids.department}
          options={departments.map((item) => ({ value: item.department_id, label: `${item.name} (${item.code})` }))}
          onChange={(value) => setup.choose('department', value)}
        />
      ) : (
        <div className="quick-grid">
          <TextField
            label="Department name"
            value={name}
            onChange={setName}
            placeholder="Computer Science and Engineering"
          />
          <TextField label="Department code" value={code} onChange={setCode} placeholder="CSE" />
        </div>
      )}
    </StepFrame>
  )
}

export function ProgramStep({ setup }: { setup: QuickSetupState }) {
  const { programs } = setup.data
  const [mode, setMode] = useState<'existing' | 'new'>(programs.length ? 'existing' : 'new')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [degree, setDegree] = useState('B.Tech')
  const [duration, setDuration] = useState('4')
  const years = Number(duration)
  const problem =
    mode === 'existing'
      ? setup.ids.program
        ? ''
        : 'Choose a program.'
      : nameCodeError(name, code) || (!degree.trim() || !(years > 0) ? 'Enter the degree type and duration.' : '')
  return (
    <StepFrame
      setup={setup}
      title="Program"
      description="The degree or diploma this department offers."
      onBack={() => setup.goTo('department')}
      continueLabel="Continue"
      continueDisabled={Boolean(problem)}
      onContinue={() =>
        void setup.perform(async () => {
          if (mode === 'existing') return
          const created = await setup.api.createAcademic('programs', {
            department_id: setup.ids.department,
            name: name.trim(),
            code: code.trim(),
            degree_type: degree.trim(),
            duration_years: years,
            total_credits: null,
            description: null,
            is_active: true,
          })
          setup.choose('program', created.program_id)
        }, 'calendar')
      }
    >
      <ModeChoice name="program-mode" mode={mode} hasExisting={programs.length > 0} noun="program" onChange={setMode} />
      {mode === 'existing' ? (
        <SelectField
          label="Program"
          value={setup.ids.program}
          options={programs.map((item) => ({
            value: item.program_id,
            label: `${item.name} (${item.duration_years} years)`,
          }))}
          onChange={(value) => setup.choose('program', value)}
        />
      ) : (
        <div className="quick-grid">
          <TextField label="Program name" value={name} onChange={setName} placeholder="B.Tech Computer Science" />
          <TextField label="Program code" value={code} onChange={setCode} placeholder="BTCS" />
          <TextField label="Degree type" value={degree} onChange={setDegree} />
          <TextField
            label="Duration (years)"
            type="number"
            min={0.5}
            step="any"
            value={duration}
            onChange={setDuration}
            help="In years, not semesters. A 4-year degree is 4."
          />
        </div>
      )}
    </StepFrame>
  )
}
