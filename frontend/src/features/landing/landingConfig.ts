export type GatewayRole = 'public' | 'institution' | 'super_admin'

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
    role: 'institution',
    label: 'Sign In',
    description:
      'Students, faculty, staff and university admins sign in here. Your workspace opens automatically for your account.',
    href: '/login',
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
