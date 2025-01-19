from fastapi import APIRouter
from app.api.v1.endpoints import admin, services, appointments

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])