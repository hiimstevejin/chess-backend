from fastapi import FastAPI
from app.api.router import api_router

def create_app() -> FastAPI:
    app = FastAPI(title="Chess Backend Engine API")

    # Include all API routes
    app.include_router(api_router)

    return app

app = create_app()
