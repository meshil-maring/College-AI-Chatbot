import { useEffect, useRef, useState } from 'react'
import { saveChoiceGroup } from '../../../../../../services/academics/semesterRegistration.ts'
import { createStructureRecord, getAcademicStructure } from '../../../../../../services/admin/academicStructure.ts'
import type { CurriculumSubject, CurriculumVersion } from '../../../../../../types/academicStructure.ts'
import type { StudyPlanChoicesState } from '../useStudyPlanChoices.ts'
import type { AcademicStructureState } from '../../../structure/useAcademicStructure.ts'

export function useCloneStudyPlan(
  state: AcademicStructureState,
  source: CurriculumVersion,
  choices: StudyPlanChoicesState,
  onCloned: (id: string) => void,
) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(`${source.name} Copy`)
  const [version, setVersion] = useState(`${source.version}-copy`)
  const [academicYearId, setAcademicYearId] = useState(source.academic_year_id)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [partialSourceId, setPartialSourceId] = useState('')
  const lock = useRef(false)
  const previousSourceId = useRef(source.curriculum_version_id)
  const live = useRef({ state, source, choices, onCloned })
  live.current = { state, source, choices, onCloned }

  useEffect(() => {
    setName(`${source.name} Copy`)
    setVersion(`${source.version}-copy`)
    setAcademicYearId(source.academic_year_id)
    if (previousSourceId.current !== source.curriculum_version_id) {
      previousSourceId.current = source.curriculum_version_id
      setError('')
    }
  }, [source.curriculum_version_id, source.name, source.version, source.academic_year_id])

  async function clone() {
    if (lock.current || source.status === 'draft' || !state.canManage('curriculum_versions')) return
    lock.current = true
    setSaving(true)
    setError('')
    let createdId: string | undefined
    try {
      const current = live.current
      const context = current.state.context
      const academicYear = current.state.catalogue?.records.academic_years?.find(
        (item) =>
          item.academic_year_id === academicYearId && item.institution_id === context.institutionId && item.is_active,
      )
      if (!name.trim() || !version.trim() || !academicYear)
        throw new Error('Enter a curriculum name and version, and choose an active academic year.')
      if (!current.state.canManage('curriculum_subjects'))
        throw new Error('You need permission to manage curriculum subjects before cloning this study plan.')

      const fresh = await getAcademicStructure(context.accessToken)
      const sourceVersion = fresh.records.curriculum_versions?.find(
        (item) =>
          item.curriculum_version_id === current.source.curriculum_version_id &&
          item.institution_id === context.institutionId,
      )
      const sourceSubjects = (fresh.records.curriculum_subjects ?? []).filter(
        (item) =>
          item.institution_id === context.institutionId &&
          item.curriculum_version_id === current.source.curriculum_version_id,
      )
      if (
        fresh.institution_id !== context.institutionId ||
        !fresh.manageable.includes('curriculum_versions') ||
        !fresh.manageable.includes('curriculum_subjects') ||
        !sourceVersion ||
        sourceVersion.status === 'draft'
      )
        throw new Error('This study plan or your access changed. Refresh and try again.')

      const sourceStages = fresh.records.program_semesters ?? []
      if (
        sourceSubjects.some(
          (subject) =>
            !sourceStages.some(
              (stage) =>
                stage.institution_id === context.institutionId &&
                stage.program_semester_id === subject.program_semester_id &&
                stage.program_id === sourceVersion.program_id &&
                stage.semester_number <= sourceVersion.total_semesters,
            ),
        )
      )
        throw new Error('Some subjects are linked to unavailable semesters. Resolve those links before cloning.')

      const groupResult = await current.choices.query.refetch()
      if (groupResult.isError || groupResult.data?.institution_id !== context.institutionId)
        throw new Error('Student choice data could not be verified. Retry after refreshing the study plan.')
      const sourceGroups = groupResult.data.groups.filter(
        (group) =>
          group.institution_id === context.institutionId &&
          group.curriculum_version_id === sourceVersion.curriculum_version_id,
      )
      if (
        sourceGroups.length &&
        (!groupResult.data.can_manage_choices ||
          sourceGroups.some((group) =>
            group.options.some((option) =>
              option.curriculum_subject_ids.some(
                (id) =>
                  !sourceSubjects.some(
                    (subject) => subject.curriculum_subject_id === id && subject.is_active && !subject.is_required,
                  ),
              ),
            ),
          ))
      )
        throw new Error(
          'Student choices cannot be cloned safely. Check choice permissions and active optional subjects.',
        )

      const copied = await createStructureRecord(context.accessToken, 'curriculum_versions', {
        program_id: sourceVersion.program_id,
        academic_year_id: academicYearId,
        name: name.trim(),
        version: version.trim(),
        total_semesters: sourceVersion.total_semesters,
        description: sourceVersion.description,
        is_active: true,
      })
      createdId = copied.curriculum_version_id
      if (
        !createdId ||
        copied.institution_id !== context.institutionId ||
        copied.program_id !== sourceVersion.program_id ||
        copied.status !== 'draft' ||
        !copied.is_active
      )
        throw new Error('The copied curriculum could not be verified for this institution.')

      const subjectIds = new Map<string, string>()
      for (const subject of sourceSubjects) {
        const result: CurriculumSubject = await createStructureRecord(context.accessToken, 'curriculum_subjects', {
          curriculum_version_id: createdId,
          program_semester_id: subject.program_semester_id,
          course_id: subject.course_id,
          course_type: subject.course_type,
          is_required: subject.is_required,
          is_active: subject.is_active,
        })
        if (
          result.institution_id !== context.institutionId ||
          result.curriculum_version_id !== createdId ||
          result.course_id !== subject.course_id ||
          result.program_semester_id !== subject.program_semester_id
        )
          throw new Error('A copied subject could not be verified. The new draft was kept for recovery.')
        subjectIds.set(subject.curriculum_subject_id, result.curriculum_subject_id)
      }

      for (const group of sourceGroups) {
        const result = await saveChoiceGroup(context.accessToken, {
          curriculum_version_id: createdId,
          program_semester_id: group.program_semester_id,
          name: group.name,
          options: group.options.map((option) => ({
            name: option.name,
            curriculum_subject_ids: option.curriculum_subject_ids.map((id) => {
              const copiedSubjectId = subjectIds.get(id)
              if (!copiedSubjectId) throw new Error('A choice references a subject that was not copied.')
              return copiedSubjectId
            }),
          })),
        })
        if (!result.choice_group_id || result.institution_id !== context.institutionId)
          throw new Error('A copied student choice could not be verified. The new draft was kept for recovery.')
      }
      await current.state.refresh()
      await current.choices.query.refetch()
      current.onCloned(createdId)
      setOpen(false)
    } catch (cause) {
      if (createdId) {
        try {
          await live.current.state.refresh()
          await live.current.choices.query.refetch()
          setPartialSourceId(live.current.source.curriculum_version_id)
          setError(
            `${cause instanceof Error ? cause.message : 'Cloning could not finish.'} The partial draft was kept. Select it from the curriculum list to review and complete it; do not retry this clone.`,
          )
        } catch {
          setError('The draft may have been created, but the lists could not refresh. Reload before retrying.')
        }
      } else {
        setError(cause instanceof Error ? cause.message : 'The study plan could not be cloned.')
      }
    } finally {
      lock.current = false
      setSaving(false)
    }
  }

  const years =
    state.catalogue?.records.academic_years?.filter(
      (item) => item.institution_id === state.context.institutionId && item.is_active,
    ) ?? []
  const canClone =
    source.status !== 'draft' &&
    state.canManage('curriculum_versions') &&
    partialSourceId !== source.curriculum_version_id
  return {
    open,
    name,
    version,
    academicYearId,
    years,
    saving,
    error,
    partialDraft: partialSourceId === source.curriculum_version_id,
    canClone,
    setName,
    setVersion,
    setAcademicYearId,
    show: () => {
      setError('')
      setOpen(true)
    },
    close: () => {
      if (!saving) setOpen(false)
    },
    clone,
  }
}
