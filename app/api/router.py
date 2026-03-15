from fastapi import APIRouter
from app.api import puzzles
from app.api.websockets import game

api_router = APIRouter()

api_router.include_router(puzzles.router, prefix="/api/puzzles")

# Register the websocket game router
api_router.include_router(game.router, prefix="/ws/game", tags=["game"])
