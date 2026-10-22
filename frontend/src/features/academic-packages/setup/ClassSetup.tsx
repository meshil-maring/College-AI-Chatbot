import { useState } from 'react'
import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { Select } from '../forms/PackageFields.tsx'
import { canManage, find, formatDeadline, isLocked, labelForId, rows, value } from '../packagePresentation.ts'
import ClassDefinitionForm from './ClassDefinitionForm.tsx'
import ClassRelationships from './ClassRelationships.tsx'
import ClassPolicyForm from './ClassPolicyForm.tsx'
import { PackageSubjects } from '../PackageSubjects.tsx'

export default function ClassSetup({
  data,
  state,
  onCreateProgram,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  onCreateProgram?: () => void
}) {
  const [classId, setClassId] = useState('')
  const academicClass = find(data, 'classes', classId)
  const mappings = rows(data, 'class_subjects').filter((row) => value(row, 'class_id') === classId)
  const available = rows(data, 'class_packages').filter((row) => value(row, 'class_id') === classId)
  return (
    <div className="package-layout">
      <div>
        {canManage(data, 'class') && (
          <ClassDefinitionForm data={data} state={state} onCreateProgram={onCreateProgram} />
        )}
        <section className="academic-panel package-card package-form">
          <h3>Class detail</h3>
          <Select
            data={data}
            source="classes"
            name="view_class"
            title="Shared class"
            selected={classId}
            onChange={setClassId}
          />
        </section>
        {academicClass && canManage(data, 'class') && (
          <>
            <ClassPolicyForm
              key={`${classId}:${value(academicClass, 'change_cutoff')}:${String(academicClass.student_choice_enabled)}`}
              state={state}
              academicClass={academicClass}
            />
            <ClassRelationships key={classId} data={data} state={state} academicClass={academicClass} />
          </>
        )}
      </div>
      <div>
        {academicClass ? (
          <>
            <section className="academic-panel package-card">
              <h3>{value(academicClass, 'code') || `Section ${value(academicClass, 'section_code')}`}</h3>
              <p>
                {labelForId(data, 'programs', value(academicClass, 'program_id'))} · Batch{' '}
                {labelForId(data, 'batches', value(academicClass, 'batch_id'))}
              </p>
              <p>
                {labelForId(data, 'semesters', value(academicClass, 'semester_id'))} · Study semester{' '}
                {value(academicClass, 'study_semester')}
              </p>
              <p>{labelForId(data, 'curricula', value(academicClass, 'curriculum_id'))}</p>
              <p>
                Initial student choice:{' '}
                {academicClass.student_choice_enabled === true ? 'Enabled' : 'Administration assigns'}
              </p>
              <p className={isLocked(academicClass) ? 'package-lock' : 'package-helper'}>
                {isLocked(academicClass) ? 'Package changes closed' : 'Package changes close'}:{' '}
                {formatDeadline(academicClass)}. The server enforces this deadline for every role.
              </p>
              <h4>Subject teaching groups</h4>
              {mappings.length ? (
                <ul className="package-subject-list">
                  {mappings.map((row) => (
                    <li key={value(row, 'class_subject_id') || value(row, 'curriculum_subject_id')}>
                      {labelForId(data, 'curriculum_subjects', value(row, 'curriculum_subject_id'))} →{' '}
                      {labelForId(data, 'sections', value(row, 'section_id'))}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="package-helper">No teaching groups mapped yet.</p>
              )}
            </section>
            <h3>Class packages</h3>
            <div className="package-records">
              {available.map((row) => (
                <article className="package-record" key={value(row, 'class_package_id') || value(row, 'package_id')}>
                  <h4>{value(row, 'selection_code') || labelForId(data, 'packages', value(row, 'package_id'))}</h4>
                  <span className="package-badge">
                    {row.enabled === false ? 'Unavailable for new choices' : 'Available'}
                  </span>
                  <PackageSubjects data={data} packageId={value(row, 'package_id')} />
                </article>
              ))}
            </div>
          </>
        ) : (
          <p className="academic-empty">
            Finish the curriculum's subjects and packages first. Then create a class, enable its packages, and prepare
            the subject teaching groups here.
          </p>
        )}
      </div>
    </div>
  )
}
