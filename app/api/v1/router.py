from fastapi import APIRouter

from app.api.v1.endpoints import (
    attachments,
    auth,
    batch_data,
    batches,
    best_batches,
    experiments,
    members,
    plans,
    researchers,
    results,
)


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(members.router, prefix="/members", tags=["Members"])
api_router.include_router(researchers.router, prefix="/researchers", tags=["Researchers"])
api_router.include_router(plans.router, prefix="/plans", tags=["Plans"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["Experiments"])
api_router.include_router(batches.router, prefix="/batches", tags=["Batches"])
api_router.include_router(best_batches.router, prefix="/best-batches", tags=["Best Batches"])
api_router.include_router(batch_data.router, prefix="/batch-data", tags=["Batch Data"])
api_router.include_router(results.router, prefix="/results", tags=["Results"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["Attachments"])
