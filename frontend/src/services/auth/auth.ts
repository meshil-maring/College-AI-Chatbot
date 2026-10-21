export { AuthError, authErrorMessage, type AuthErrorKind } from './errors.ts'
export {
  authenticate,
  changePassword,
  completePasswordReset,
  fetchCurrentUser,
  isEmailAddress,
  login,
  refreshSession,
  requestPasswordRecovery,
  revokeSession,
  studentLogin,
  type AuthMessageResponse,
} from './session.ts'
