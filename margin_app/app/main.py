"""
Main entry point for the application.
"""

from fastapi import FastAPI

app = FastAPI()


from app.api.liquidation import router as liquidation_router

app.include_router(liquidation_router, prefix="/api/liquidation", tags=["liquidation"])
