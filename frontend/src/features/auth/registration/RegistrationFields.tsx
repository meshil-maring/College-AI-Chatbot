import PasswordField from '../password/PasswordField.tsx'
import type { RegistrationFormModel } from './useRegistrationForm.ts'
import { INPUT_CLASS } from './useRegistrationForm.ts'

export function RegistrationFields({ model }: { model: RegistrationFormModel }) {
  const {
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
    handleInstitutionBlur,
    handleSubmit,
  } = model
  return (
    <form
      className="mt-6 flex flex-col gap-5"
      onSubmit={(event) => {
        void handleSubmit(event)
      }}
      noValidate
      aria-busy={submitting}
    >
      <label className="flex flex-col gap-1 text-sm text-muted">
        Full Name
        <input
          type="text"
          name="fullName"
          required
          autoComplete="name"
          disabled={submitting}
          placeholder="Jane Doe"
          className={INPUT_CLASS}
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm text-muted">
        Email
        <input
          type="email"
          name="email"
          required
          autoComplete="email"
          disabled={submitting}
          placeholder="student@college.edu"
          className={INPUT_CLASS}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>
      {registrationType === 'student' ? (
        <>
          <label className="flex flex-col gap-1 text-sm text-muted">
            Register Number
            <input
              type="text"
              name="registerNumber"
              autoComplete="off"
              disabled={submitting}
              placeholder="e.g. 1001"
              className={INPUT_CLASS}
              value={registerNumber}
              onChange={(event) => setRegisterNumber(event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-muted">
            University Roll Number
            <input
              type="text"
              name="universityRollNumber"
              autoComplete="off"
              disabled={submitting}
              placeholder="e.g. 2026-1001"
              className={INPUT_CLASS}
              value={universityRollNumber}
              onChange={(event) => setUniversityRollNumber(event.target.value)}
            />
          </label>
        </>
      ) : (
        <>
          <label className="flex flex-col gap-1 text-sm text-muted">
            Designation <span className="text-xs text-muted">(optional)</span>
            <input
              type="text"
              name="designation"
              disabled={submitting}
              placeholder="e.g. Assistant Professor"
              className={INPUT_CLASS}
              value={designation}
              onChange={(event) => setDesignation(event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-muted">
            Department <span className="text-xs text-muted">(optional)</span>
            <input
              type="text"
              name="department"
              disabled={submitting}
              placeholder="e.g. Computer Science"
              className={INPUT_CLASS}
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
            />
          </label>
        </>
      )}
      <label className="flex flex-col gap-1 text-sm text-muted">
        Institution Code
        <input
          type="text"
          name="institutionCode"
          required
          autoComplete="off"
          disabled={submitting}
          placeholder="ABC001"
          className={INPUT_CLASS}
          aria-describedby="institution-status"
          value={institutionCode}
          onChange={(event) => {
            institutionLookupGeneration.current += 1
            setInstitutionCode(event.target.value)
            // Typing invalidates the previous resolution; the code is
            // re-verified on blur (or right before submission).
            setResolvedInstitution(null)
            setInstitutionStatus('idle')
            setInstitutionMessage(null)
          }}
          onBlur={handleInstitutionBlur}
        />
      </label>
      <div id="institution-status" aria-live="polite">
        {institutionStatus === 'checking' && (
          <p role="status" className="text-sm text-muted">
            Finding institution…
          </p>
        )}
        {institutionStatus === 'found' && resolvedInstitution !== null && (
          <p role="status" className="text-sm text-success">
            {resolvedInstitution.name}
          </p>
        )}
        {(institutionStatus === 'invalid' || institutionStatus === 'not_accepting' || institutionStatus === 'error') &&
          institutionMessage !== null && (
            <p role="alert" className="text-sm text-danger">
              {institutionMessage}
            </p>
          )}
      </div>
      <PasswordField
        label="Password"
        name="password"
        value={password}
        onChange={setPassword}
        required
        minLength={8}
        maxLength={128}
        autoComplete="new-password"
        disabled={submitting}
        placeholder="••••••••"
      />
      <PasswordField
        label="Confirm Password"
        name="confirmPassword"
        value={confirmPassword}
        onChange={setConfirmPassword}
        required
        minLength={8}
        maxLength={128}
        autoComplete="new-password"
        disabled={submitting}
        placeholder="••••••••"
      />
      <button
        type="submit"
        disabled={submitting}
        className="rounded-lg bg-accent px-4 py-2 font-semibold text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? 'Creating account…' : 'Create Account'}
      </button>
      <button
        type="button"
        disabled={submitting}
        onClick={onBackToLogin}
        className="text-sm text-muted hover:text-content underline"
      >
        Already have an account? Back to Login
      </button>
    </form>
  )
}
