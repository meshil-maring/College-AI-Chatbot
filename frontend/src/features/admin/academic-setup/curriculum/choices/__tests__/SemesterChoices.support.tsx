import { catalogue, structureCatalogue } from '../../semester-plan/__tests__/StudyPlan.support.tsx'
import { beforeEach } from 'vitest'
import { fireEvent, screen, within } from '@testing-library/react'

export {
  auth,
  catalogue,
  structureCatalogue,
  renderPlan,
  selectPlan,
  StudyPlanWorkspace,
} from '../../semester-plan/__tests__/StudyPlan.support.tsx'
export { registrationCatalogue } from '../../../__tests__/AcademicSetup.support.ts'
export * as api from '../../../../../../services/academics/semesterRegistration.ts'

beforeEach(() => {
  catalogue.records.courses!.push({
    ...catalogue.records.courses![0],
    course_id: 'optional-course',
    name: 'DBMS',
    code: 'DBMS',
  })
  structureCatalogue.records.curriculum_subjects!.push({
    ...structureCatalogue.records.curriculum_subjects![0],
    curriculum_subject_id: 'optional-mapping',
    course_id: 'optional-course',
    is_required: false,
  })
})

export const savedGroup = {
  choice_group_id: 'saved-group',
  institution_id: 'institution-1',
  curriculum_version_id: 'version-1',
  program_semester_id: 'stage-1',
  name: 'Science choices',
  options: [
    { choice_option_id: 'option-a', name: 'Database studies', curriculum_subject_ids: ['optional-mapping'] },
    { choice_option_id: 'option-b', name: 'Database and labs', curriculum_subject_ids: ['optional-mapping'] },
  ],
}

export function semesterChoices(number = 1) {
  return within(screen.getByRole('region', { name: `Student choices in Semester ${number}` }))
}

export function openChoices(number = 1) {
  fireEvent.click(semesterChoices(number).getByRole('button', { name: 'Add choice group' }))
  return within(semesterChoices(number).getByRole('form', { name: 'Subject choice group' }))
}

export function fillChoices(form: ReturnType<typeof within>, name = 'Science choices') {
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: name } })
  for (const checkbox of form.getAllByRole('checkbox', { name: 'DBMS' })) fireEvent.click(checkbox)
}
