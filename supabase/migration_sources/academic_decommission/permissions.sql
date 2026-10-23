-- Account-role assignments and identity/approval permissions stay intact.
-- Remove only grants for the explicitly retired academic permission families.
DELETE FROM public.user_permission_grants WHERE permission_id IN(SELECT permission_id FROM academic_decommission_permissions);
DELETE FROM public.role_permissions WHERE permission_id IN(SELECT permission_id FROM academic_decommission_permissions);
DELETE FROM public.permissions WHERE permission_id IN(SELECT permission_id FROM academic_decommission_permissions);
