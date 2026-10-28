import { useEffect, useRef, useState } from 'react'
import {
  RegistrationError,
  registerFaculty,
  registerStaff,
  registerStudent,
  registrationErrorMessage,
} from '../../../services/registration/registration.ts'
import type { RegistrationResponse, RegistrationType } from '../../../types/registration.ts'
import { useInstitutionLookup } from './useInstitutionLookup.ts'
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const INPUT_CLASS =
  'rounded-lg border border-control bg-surface px-3 py-2 text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent'

export interface RegistrationFormProps {
  /** Navigate back to the login screen (existing conditional navigation). */
  onBackToLogin: () => void
  registrationType?: RegistrationType
}

export function useRegistrationForm({ onBackToLogin, registrationType = 'student' }: RegistrationFormProps) {
  const {
    institutionCode,
    setInstitutionCode,
    institutionLookupGeneration,
    resolvedInstitution,
    setResolvedInstitution,
    institutionStatus,
    setInstitutionStatus,
    institutionMessage,
    setInstitutionMessage,
    isResolvedFor,
    handleInstitutionBlur,
    resolveInstitution,
  } = useInstitutionLookup()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [registerNumber, setRegisterNumber] = useState('')
  const [universityRollNumber, setUniversityRollNumber] = useState('')
  const [designation, setDesignation] = useState('')
  const [department, setDepartment] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<RegistrationResponse | null>(null)
  const confirmationTitleRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (success !== null) confirmationTitleRef.current?.focus()
  }, [success])

  /**
   * Client-side validation mirroring the backend contract exactly — never
   * stricter (password >= 8; names non-blank; at least one academic
   * identifier required).
   */
  function validate(): string | null {
    if (fullName.trim().length < 2) {
      return 'Please enter your full name.'
    }
    if (!EMAIL_PATTERN.test(email.trim())) {
      return 'Please enter a valid email address.'
    }
    if (registrationType === 'student' && registerNumber.trim() === '' && universityRollNumber.trim() === '') {
      return 'Enter at least one of register number or university roll number.'
    }
    if (institutionCode.trim().length < 2) {
      return 'Enter your institution code (e.g. ABC001).'
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters.'
    }
    if (confirmPassword !== password) {
      return 'Passwords do not match.'
    }
    return null
  }

  /**
   * Split the single Full Name field into the backend's required first_name /
   * last_name. With one token only, the token is reused as the last name so
   * the backend's non-blank rule is met without rejecting the student.
   */
  function splitFullName(value: string): { first_name: string; last_name: string } {
    const tokens = value.trim().split(/\s+/)
    const first = tokens[0] ?? ''
    const rest = tokens.slice(1).join(' ')
    return { first_name: first, last_name: rest || first }
  }

  async function handleSubmit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (submitting) return
    setError(null)
    const validationError = validate()
    if (validationError !== null) {
      setError(validationError)
      return
    }

    setSubmitting(true)
    try {
      const code = institutionCode.trim()
      // Registration must never submit with an unverified institution:
      // resolve on demand when the code changed (or was never looked up).
      const resolved = isResolvedFor(code) ? resolvedInstitution : await resolveInstitution(code)
      if (resolved === null) {
        return // the institution status region already explains the problem
      }
      const { first_name, last_name } = splitFullName(fullName)
      const request = {
        registration_type: registrationType,
        institution_code: resolved.code,
        email: email.trim(),
        password,
        first_name,
        last_name,
        ...(registrationType === 'student'
          ? {
              register_number: registerNumber.trim() || null,
              university_roll_number: universityRollNumber.trim() || null,
            }
          : {
              designation: designation.trim() || null,
              department: department.trim() || null,
            }),
      }
      const response =
        registrationType === 'faculty'
          ? await registerFaculty(request)
          : registrationType === 'staff'
            ? await registerStaff(request)
            : await registerStudent(request)
      // Pending-approval state ONLY: the response carries no token and the
      // auth state is untouched, so the student is never treated as logged in.
      setSuccess(response)
      // Phase 6.15.5 hardening (browser-storage/memory audit §20): the
      // plaintext password is dropped immediately after the submission
      // completes — it is never needed again once the account exists, and
      // it must not linger in component memory on the success screen.
      setPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(
        err instanceof RegistrationError ? registrationErrorMessage(err) : 'Something went wrong. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return {
    onBackToLogin,
    registrationType,
    fullName,
    setFullName,
    email,
    setEmail,
    registerNumber,
    setRegisterNumber,
    universityRollNumber,
    setUniversityRollNumber,
    designation,
    setDesignation,
    department,
    setDepartment,
    institutionCode,
    setInstitutionCode,
    institutionLookupGeneration,
    password,
    setPassword,
    confirmPassword,
    setConfirmPassword,
    resolvedInstitution,
    setResolvedInstitution,
    institutionStatus,
    setInstitutionStatus,
    institutionMessage,
    setInstitutionMessage,
    submitting,
    error,
    success,
    confirmationTitleRef,
    handleInstitutionBlur,
    handleSubmit,
  }
}

export type RegistrationFormModel = ReturnType<typeof useRegistrationForm>
