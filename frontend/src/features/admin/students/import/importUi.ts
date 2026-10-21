import { AlertCircle, AlertTriangle, CheckCircle2, Files } from 'lucide-react'
export const statuses = {
  valid: {
    label: 'Valid',
    title: 'Valid Records',
    description: 'Ready to import',
    Icon: CheckCircle2,
  },
  duplicate: {
    label: 'Duplicate',
    title: 'Duplicate Records',
    description: 'Already exist in system',
    Icon: Files,
  },
  invalid: {
    label: 'Invalid',
    title: 'Invalid Records',
    description: 'Missing required fields',
    Icon: AlertTriangle,
  },
  conflicting: {
    label: 'Conflicting',
    title: 'Conflicting Records',
    description: 'Data mismatch with existing',
    Icon: AlertCircle,
  },
} as const

export const steps = [
  ['Upload File', 'Select and upload'],
  ['Validate & Preview', 'Check records'],
  ['Confirm Import', 'Review and import'],
  ['Import Result', 'View summary'],
]

export const PAGE_SIZE = 8
