from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routes import router


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

settings = get_settings()


# ---------------------------------------------------------
# Application startup / shutdown
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables when the application starts
    init_db()

    yield


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "FitBuddy is an AI-powered fitness application that "
        "generates personalized workout plans and nutrition tips."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Static Files
# ---------------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

app.include_router(router)