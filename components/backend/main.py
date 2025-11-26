from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from backend.routers import reservations as reservations_router
# import routers
from backend.routers import auth as auth_router
from backend.routers import roles as roles_router
from backend.routers import departments as depts_router
from backend.routers import staff as staff_router
from backend.routers import items as items_router

app = FastAPI(title="PhysioTracker API (backend)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth_router.router)
app.include_router(roles_router.router)
app.include_router(depts_router.router)
app.include_router(staff_router.router)
app.include_router(items_router.router)
app.include_router(reservations_router.router)
# Serve static frontend from backend/frontend
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")