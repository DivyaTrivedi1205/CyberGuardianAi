from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.connection import initialize_database
from backend.routes.auth import router as auth_router
from backend.routes.security import router as security_router
from backend.routes.community import router as community_router

app = FastAPI(title="CyberGuardian AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
