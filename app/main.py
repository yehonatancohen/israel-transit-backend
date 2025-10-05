from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health, feeds, routes, sessions

app = FastAPI(title="Israel Transit MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(feeds.router, prefix="/v1/feeds", tags=["feeds"])
app.include_router(routes.router, prefix="/v1/routes", tags=["routes"])
app.include_router(sessions.router, prefix="/v1/trip", tags=["trip"])
