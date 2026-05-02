"""Discord-Endpunkte: Status, Connect/Disconnect, Config."""
from fastapi import APIRouter

from hydrahive.api.routes.communication_discord_routes import router as _routes_router

router = APIRouter()
router.include_router(_routes_router)
