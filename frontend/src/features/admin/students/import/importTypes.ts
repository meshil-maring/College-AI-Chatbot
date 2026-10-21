import type { ReactNode } from 'react'
import type { ImportStudent, ReviewStudent } from './types.ts'

export interface StudentImportOutcome {
  row: number
  name: string
  status: 'imported' | 'failed'
  message: string
}

export interface StudentRegistrationImport {
  readFile: (file: File) => Promise<ImportStudent[]>
  reviewRows: (rows: ImportStudent[]) => ReviewStudent[]
  importRows: (rows: ReviewStudent[], onProgress: (completed: number) => void) => Promise<StudentImportOutcome[]>
  onBusyChange: (busy: boolean) => void
  resultActions?: ReactNode
  onReset?: () => void
  resultsBusy?: boolean
}
