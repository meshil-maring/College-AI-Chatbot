/** Institution administrators and the Owner, who alone manages them. */
export interface InstitutionAdmin {
  user_id: string
  name: string
  email: string
  status: string
  assigned_at: string | null
  is_owner: boolean
}

export interface AdminInvitation {
  invitation_id: string
  email: string
  full_name: string | null
  expires_at: string | null
  created_at: string | null
  email_delivery_status: string | null
}

export interface InstitutionAdminList {
  owner_user_id: string | null
  /** Whether the signed-in administrator is the Owner. */
  viewer_is_owner: boolean
  administrators: InstitutionAdmin[]
  invitations: AdminInvitation[]
}

export interface InstitutionAdminResult {
  message: string
  already_applied: boolean
}
