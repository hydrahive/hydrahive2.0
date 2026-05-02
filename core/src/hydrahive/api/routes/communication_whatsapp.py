"""WhatsApp-Endpunkte: Status, Connect/Disconnect, Config, Incoming-Bridge."""
from fastapi import APIRouter

from hydrahive.api.routes.communication_whatsapp_routes import router as _routes_router
from hydrahive.api.routes.communication_whatsapp_incoming import router as _incoming_router

router = APIRouter()
router.include_router(_routes_router)
router.include_router(_incoming_router)
