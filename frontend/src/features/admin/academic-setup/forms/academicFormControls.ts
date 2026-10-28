import type { Dispatch, SetStateAction } from 'react'
import type { AcademicDraft } from '../academicSetupForm.ts'

export const academicInputClass =
  'mt-1 block w-full rounded-lg border border-control bg-surface p-2 text-content focus:outline-none focus:ring-2 focus:ring-accent'
export const academicButtonClass =
  'rounded-lg border border-control px-3 py-2 text-sm text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50'

export interface AcademicFieldsProps {
  editing: boolean
  draft: AcademicDraft
  setDraft: Dispatch<SetStateAction<AcademicDraft>>
}
