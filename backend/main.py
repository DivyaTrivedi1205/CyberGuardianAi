from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import initialize_database
from routes.auth import router as auth_router
from routes.security import router as security_router
from routes.community import router as community_router
from config import settings

# FastAPI does not support async def startup() reliably in all versions,
# so we use the on_event("startup") pattern with the config-aware initializer.
app = FastAPI(title="CyberGuardian AI API")

# CORS: use configured allowed origins instead of wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(security_router)
app.include_router(community_router)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "CyberGuardian AI Backend Running"}
