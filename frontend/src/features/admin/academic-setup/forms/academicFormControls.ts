import type { Dispatch, SetStateAction } from 'react'
import type { AcademicDraft } from '../academicSetupForm.ts'

export const academicInputClass =
  'mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 p-2 text-white focus:outline-none focus:ring-2 focus:ring-emerald-400'
export const academicButtonClass =
  'rounded-lg border border-slate-600 px-3 py-2 text-sm text-white hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-50'

export interface AcademicFieldsProps {
  editing: boolean
  draft: AcademicDraft
  setDraft: Dispatch<SetStateAction<AcademicDraft>>
}
