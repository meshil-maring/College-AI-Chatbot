import { useState } from 'react'
import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { Select } from '../forms/PackageFields.tsx'
import { find, formatDeadline, labelForId, rows, value } from '../packagePresentation.ts'
import PlacementForm from './PlacementForm.tsx'
import { AssignmentChangeForm, InitialAssignmentForm } from './AssignmentForms.tsx'
import { PackageSubjects } from '../PackageSubjects.tsx'

export default function PackageAssignments({
  data,
  state,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
}) {
  const [classId, setClassId] = useState('')
  const [assignmentId, setAssignmentId] = useState('')
  const academicClass = find(data, 'classes', classId)
  const placements = new Set(
    rows(data, 'placements')
      .filter((row) => value(row, 'class_id') === classId)
      .map((row) => value(row, 'placement_id')),
  )
  const assignments = rows(data, 'assignments').filter(
    (row) => placements.has(value(row, 'placement_id')) && row.is_active !== false,
  )
  const assignment = assignments.find((row) => value(row, 'assignment_id') === assignmentId)
  return (
    <div className="package-layout">
      <div>
        <section className="academic-panel package-card package-form">
          <h3>Class package assignments</h3>
          <Select
            data={data}
            source="classes"
            name="assignment_class"
            title="Class"
            selected={classId}
            onChange={(id) => {
              setClassId(id)
              setAssignmentId('')
            }}
          />
          {academicClass && (
            <>
              <p className="package-helper">
                {labelForId(data, 'programs', value(academicClass, 'program_id'))} · Batch{' '}
                {labelForId(data, 'batches', value(academicClass, 'batch_id'))} ·{' '}
                {labelForId(data, 'semesters', value(academicClass, 'semester_id'))} · Study semester{' '}
                {value(academicClass, 'study_semester')}
              </p>
              <p className="package-helper">Change cutoff: {formatDeadline(academicClass)}</p>
            </>
          )}
        </section>
        {academicClass && data.capabilities.includes('assign') && academicClass.can_assign !== false && (
          <PlacementForm data={data} state={state} academicClass={academicClass} />
        )}
        {academicClass && (
          <InitialAssignmentForm key={classId} data={data} state={state} academicClass={academicClass} />
        )}
      </div>
      <div>
        {!academicClass ? (
          <p className="academic-empty">
            Choose a class to see its permitted packages, student placements and current assignments.
          </p>
        ) : (
          <>
            <section className="academic-panel package-card package-form">
              <h3>Current package</h3>
              <Select
                data={data}
                source="assignments"
                name="current_assignment"
                title="Assignment"
                items={assignments}
                selected={assignmentId}
                onChange={setAssignmentId}
              />
              {assignment && (
                <>
                  <p>
                    Revision {value(assignment, 'revision')} ·{' '}
                    {labelForId(data, 'packages', value(assignment, 'package_id'))}
                  </p>
                  <PackageSubjects data={data} packageId={value(assignment, 'package_id')} />
                </>
              )}
              {!assignments.length && <p className="package-helper">No packages assigned in this class yet.</p>}
            </section>
            {assignment && (
              <AssignmentChangeForm
                key={`${assignmentId}:${value(assignment, 'revision')}`}
                data={data}
                state={state}
                academicClass={academicClass}
                assignment={assignment}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
