from fastapi import APIRouter
from app.api.websockets import game

api_router = APIRouter()

# Register the websocket game router
api_router.include_router(game.router, prefix="/ws/game", tags=["game"])
