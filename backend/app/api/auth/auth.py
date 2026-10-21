"""Authentication router composition; handlers live in feature modules."""

from fastapi import APIRouter

from app.api.auth import signup, login, password_recovery, password_change, sessions


router = APIRouter(tags=["auth"])

router.include_router(signup.router)
router.include_router(login.router)
router.include_router(password_recovery.router)
router.include_router(password_change.router)
router.include_router(sessions.router)
