from app.module.manage import ManageRouter
from app.module.pool import PoolRouter
from fastapi import APIRouter

# API Router for version 1

V1Router = APIRouter(prefix="/api/v1")
V1Router.include_router(ManageRouter)
V1Router.include_router(PoolRouter)
