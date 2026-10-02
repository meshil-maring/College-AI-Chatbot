export type GatewayRole =
  | 'public'
  | 'student'
  | 'admin'
  | 'staff'
  | 'faculty'
  | 'super_admin'

export interface GatewayEntry {
  readonly role: GatewayRole
  readonly label: string
  readonly description: string
  readonly href: string
  readonly area: 'public' | 'institution' | 'platform'
}

/**
 * Presentation-only role catalogue for the demo gateway.
 *
 * These values choose destinations and labels only. They are never sent as an
 * authentication claim and never authorize a user. AuthProvider continues to
 * obtain the canonical role from GET /auth/me after sign-in.
 */
export const GATEWAY_ENTRIES: readonly GatewayEntry[] = [
  {
    role: 'public',
    label: 'Public AI Chat',
    description: 'Ask questions about a university using public AI knowledge.',
    href: '/u',
    area: 'public',
  },
  {
    role: 'student',
    label: 'Student Login',
    description: 'Access your personalized academic information.',
    href: '/login/student',
    area: 'institution',
  },
  {
    role: 'admin',
    label: 'University Admin Login',
    description: "Manage your university's academic and public information.",
    href: '/login/admin',
    area: 'institution',
  },
  {
    role: 'staff',
    label: 'Staff Login',
    description: 'Access staff academic and operational features.',
    href: '/login/staff',
    area: 'institution',
  },
  {
    role: 'faculty',
    label: 'Teacher / Faculty Login',
    description: 'Access teaching and academic functionality.',
    href: '/login/faculty',
    area: 'institution',
  },
  {
    role: 'super_admin',
    label: 'Super Admin',
    description: 'Platform-level administration and management.',
    href: '/super-admin',
    area: 'platform',
  },
] as const

export const FUTURE_CAPABILITIES = [
  'FAQ',
  'Notices',
  'Learning Resources',
  'University Contact',
  'WhatsApp',
  'Support',
] as const

