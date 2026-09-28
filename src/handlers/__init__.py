from aiogram import Router
from .auth import router as auth_router
from .schedule import router as schedule_router
from .admin import router as admin_router
from .common import router as common_router

main_router = Router()
main_router.include_router(auth_router)
main_router.include_router(schedule_router)
main_router.include_router(admin_router)
main_router.include_router(common_router)

__all__ = ["main_router"]
