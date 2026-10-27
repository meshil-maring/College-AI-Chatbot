import '../../__tests__/AcademicSetup.support.ts'
import { render } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import { populateStructure } from '../../__tests__/academicStructureFixtures.ts'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export { stage, version, mapping, cohort, section, offering } from '../../__tests__/academicStructureFixtures.ts'
export * as api from '../../../../../services/admin/academicStructure.ts'
beforeEach(populateStructure)
export function renderStructure(page: AcademicPage = 'program-semesters') {
  return render(<AcademicWorkspace page={page} search="" onNavigate={vi.fn()} onClearSearch={vi.fn()} />)
}
