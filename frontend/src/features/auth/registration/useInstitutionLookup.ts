import { useRef, useState } from 'react'
import { RegistrationError, lookupInstitution, registrationErrorMessage } from '../../../services/registration/registration.ts'
import type { InstitutionLookupResponse } from '../../../types/registration.ts'
/** States of the institution-code resolution UX. */
export type InstitutionStatus = 'idle' | 'checking' | 'found' | 'invalid' | 'not_accepting' | 'error'
export function useInstitutionLookup() {
  const [institutionCode, setInstitutionCode] = useState(
    () => new URLSearchParams(window.location.search).get('institution')?.trim().toUpperCase() ?? '',
  )

  const institutionLookupGeneration = useRef(0)

  const [resolvedInstitution, setResolvedInstitution] = useState<InstitutionLookupResponse | null>(null)

  const [institutionStatus, setInstitutionStatus] = useState<InstitutionStatus>('idle')

  const [institutionMessage, setInstitutionMessage] = useState<string | null>(null)

  /** True when the stored resolution belongs to the currently typed code. */
  function isResolvedFor(code: string): boolean {
    return resolvedInstitution !== null && resolvedInstitution.code.toUpperCase() === code.trim().toUpperCase()
  }

  /** Clear the resolution when the code field is emptied. */
  function handleInstitutionBlur(): void {
    const code = institutionCode.trim()
    if (code.length === 0) {
      setResolvedInstitution(null)
      setInstitutionStatus('idle')
      setInstitutionMessage(null)
      return
    }
    if (!isResolvedFor(code)) {
      void resolveInstitution(code)
    }
  }

  /**
   * Resolve the typed institution code through the public lookup endpoint.
   * Raw API errors are never surfaced — only the controlled messages below.
   */
  async function resolveInstitution(rawCode: string): Promise<InstitutionLookupResponse | null> {
    const generation = ++institutionLookupGeneration.current
    const code = rawCode.trim()
    if (code.length < 2) {
      setResolvedInstitution(null)
      setInstitutionStatus('invalid')
      setInstitutionMessage('Enter your institution code (e.g. ABC001).')
      return null
    }
    setInstitutionStatus('checking')
    setInstitutionMessage('Finding institution…')
    try {
      const found = await lookupInstitution(code)
      if (generation !== institutionLookupGeneration.current) return null
      setResolvedInstitution(found)
      setInstitutionStatus('found')
      setInstitutionMessage(null)
      return found
    } catch (err) {
      if (generation !== institutionLookupGeneration.current) return null
      setResolvedInstitution(null)
      if (err instanceof RegistrationError) {
        if (err.kind === 'institution_not_found') {
          setInstitutionStatus('invalid')
          setInstitutionMessage('Institution code was not found. Please check the code and try again.')
          return null
        }
        if (err.kind === 'institution_not_accepting') {
          setInstitutionStatus('not_accepting')
          setInstitutionMessage('This institution is not currently accepting registrations.')
          return null
        }
        setInstitutionStatus('error')
        setInstitutionMessage(registrationErrorMessage(err))
        return null
      }
      setInstitutionStatus('error')
      setInstitutionMessage('Could not verify the institution code right now. Please try again.')
      return null
    }
  }
  return {
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
  }
}
