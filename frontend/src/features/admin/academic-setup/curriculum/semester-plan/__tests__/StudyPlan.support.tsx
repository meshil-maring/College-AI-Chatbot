import '../../../__tests__/AcademicSetup.support.ts'
import { catalogue, structureCatalogue } from '../../../__tests__/AcademicSetup.support.ts'
import { populateStructure, stage } from '../../../__tests__/academicStructureFixtures.ts'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import { useState } from 'react'
import AcademicWorkspace from '../../../overview/AcademicWorkspace.tsx'
import type { AcademicPage } from '../../../overview/academicOverviewModel.ts'

export { auth, catalogue, structureCatalogue } from '../../../__tests__/AcademicSetup.support.ts'
export * as api from '../../../../../../services/admin/academicStructure.ts'

beforeEach(() => {
  populateStructure()
  Object.assign(structureCatalogue.records.curriculum_versions![0], {
    status: 'draft',
    published_at: null,
    total_semesters: 2,
  })
  structureCatalogue.records.program_semesters!.push({
    ...stage,
    program_semester_id: 'stage-2',
    semester_number: 2,
    name: 'Semester 2',
    code: 'S2',
  })
  catalogue.records.courses!.push({
    ...catalogue.records.courses![0],
    course_id: 'english',
    name: 'English',
    code: 'ENG',
  })
})

export function StudyPlanWorkspace() {
  const [page, setPage] = useState<AcademicPage>('curriculum-subjects')
  return <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
}

export function renderPlan() {
  return render(<StudyPlanWorkspace />)
}

export async function selectPlan() {
  fireEvent.change(await screen.findByRole('combobox', { name: 'Choose a curriculum' }), {
    target: { value: 'version-1' },
  })
  await screen.findByRole('region', { name: 'Semester 1 subjects' })
}
