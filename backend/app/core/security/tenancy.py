"""Security tenancy responsibilities."""

from uuid import UUID

from app.core.errors import AppError


def user_tenant_id(current_user: dict) -> UUID | None:
    """Return the authenticated user's tenant (institution_id), or None."""
    raw = current_user.get("institution_id") if current_user else None
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _tenant_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different institution",
        status_code=403,
        code="TENANT_MISMATCH",
    )


def scope_tenant(
    current_user: dict,
    requested: UUID | str | None,
) -> UUID | None:
    """Resolve the effective tenant for a request that carries an institution id.

    * Tenant-bound user + requested institution  -> must match, else 403.
    * Tenant-bound user + no requested institution -> own tenant.
    * Platform-level user (no tenant)            -> requested passed through.
    """
    tenant = user_tenant_id(current_user)
    if tenant is None:
        # Platform-level account: pass the requested institution through.
        return requested if not isinstance(requested, str) else UUID(requested)
    if requested is not None and UUID(str(requested)) != tenant:
        raise _tenant_mismatch()
    return tenant


def assert_tenant_object(
    current_user: dict,
    institution_id: UUID | str | None,
) -> None:
    """Guard a fetched/created row against cross-tenant access.

    Rows with institution_id=None are global and visible to everyone.
    Tenant-bound users may only access rows belonging to their own tenant.
    """
    tenant = user_tenant_id(current_user)
    if tenant is None or institution_id is None:
        return
    if UUID(str(institution_id)) != tenant:
        raise _tenant_mismatch()
