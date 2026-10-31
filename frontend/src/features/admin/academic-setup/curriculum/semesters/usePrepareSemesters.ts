import { useEffect, useRef, useState } from 'react'
import { createStructureRecord, getAcademicStructure } from '../../../../../services/admin/academicStructure.ts'
import type { CurriculumVersion } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import { studyPlanCanChange, studyPlanSemesters } from '../semester-plan/studyPlanModel.ts'

// Reuse the existing, audited stage API. A failed batch keeps completed stages;
// every explicit retry reads the server again and creates only missing numbers.
export function usePrepareSemesters(state: AcademicStructureState, version?: CurriculumVersion, hasDrafts = false) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const mounted = useRef(true)
  const locked = useRef(false)
  const live = useRef({ state, version, hasDrafts })
  live.current = { state, version, hasDrafts }
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const missing = version ? studyPlanSemesters(state, version).filter((item) => !item.semester).length : 0
  const canPrepare = Boolean(
    version && missing && !hasDrafts && studyPlanCanChange(state, version) && state.canManage('program_semesters'),
  )

  async function prepare() {
    if (!mounted.current || locked.current || !canPrepare || !version) return
    locked.current = true
    setSaving(true)
    setError('')
    setNotice('')
    const identity = state.context.identity
    const versionId = version.curriculum_version_id
    const current = () =>
      mounted.current &&
      live.current.state.context.identity === identity &&
      live.current.version?.curriculum_version_id === versionId
    const allowed = () =>
      current() &&
      !live.current.hasDrafts &&
      live.current.state.canManage('program_semesters') &&
      studyPlanCanChange(live.current.state, live.current.version!)
    try {
      const fresh = await getAcademicStructure(live.current.state.context.accessToken)
      if (!current()) return
      const latestVersion = fresh.records.curriculum_versions?.find(
        (item) => item.curriculum_version_id === versionId && item.institution_id === state.context.institutionId,
      )
      if (
        !allowed() ||
        fresh.institution_id !== state.context.institutionId ||
        !fresh.manageable.includes('program_semesters') ||
        !fresh.records.program_semesters ||
        latestVersion?.status !== 'draft' ||
        !latestVersion.is_active ||
        latestVersion.program_id !== version.program_id ||
        latestVersion.total_semesters !== version.total_semesters
      )
        throw new Error('Semester setup is unavailable. Refresh the study plan and check your access.')
      const semesters = fresh.records.program_semesters.filter(
        (item) => item.institution_id === state.context.institutionId && item.program_id === version.program_id,
      )
      const codes = new Set(semesters.map((item) => item.code.trim().toLowerCase()))
      for (let number = 1; number <= version.total_semesters; number += 1) {
        if (!current()) return
        if (!allowed()) throw new Error('Your access or study plan changed. Refresh before continuing.')
        if (semesters.some((item) => item.semester_number === number)) continue
        let code = `SEM-${number}`
        for (let suffix = 2; codes.has(code.toLowerCase()); suffix += 1) code = `SEM-${number}-${suffix}`
        const result = await createStructureRecord(live.current.state.context.accessToken, 'program_semesters', {
          program_id: version.program_id,
          semester_number: number,
          name: `Semester ${number}`,
          code,
          is_active: true,
        })
        if (!current()) return
        if (
          !result.program_semester_id ||
          result.institution_id !== state.context.institutionId ||
          result.program_id !== version.program_id ||
          result.semester_number !== number ||
          !result.is_active
        )
          throw new Error('The saved semester could not be verified for this program.')
        semesters.push(result)
        codes.add(result.code.trim().toLowerCase())
      }
      if (current()) setNotice('Semesters are ready. Existing semester records have been reused.')
    } catch (cause) {
      if (current())
        setError(
          `${cause instanceof Error ? cause.message : 'Semester setup could not finish.'} Saved semesters are kept. Retry to create only those still missing.`,
        )
    } finally {
      // A saved write stays saved even if the following catalogue read fails.
      if (current()) {
        try {
          const results = await live.current.state.refresh()
          if (current() && results.some((result) => result.isError)) {
            setNotice('')
            setError('Semester changes were saved, but the list could not refresh. Use Retry above to reload it.')
          }
        } catch {
          if (current()) setError('Could not refresh semesters. Reload the study plan before continuing.')
        }
      }
      locked.current = false
      if (mounted.current) setSaving(false)
    }
  }
  return { missing, canPrepare, saving, error, notice, prepare }
}
