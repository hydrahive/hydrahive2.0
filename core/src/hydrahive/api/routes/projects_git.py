"""Git-Routen pro Projekt — aggregiert manage + ops."""
from fastapi import APIRouter

from hydrahive.api.routes.projects_git_manage import router as _manage_router
from hydrahive.api.routes.projects_git_ops import router as _ops_router
from hydrahive.api.routes.projects_git_gitea import router as _gitea_router

router = APIRouter()
router.include_router(_manage_router)
router.include_router(_ops_router)
router.include_router(_gitea_router)
